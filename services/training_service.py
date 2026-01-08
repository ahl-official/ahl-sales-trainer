import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

from extensions import db
from config_logging import get_logger
from services.pinecone_service import get_namespaces_for_category, query_pinecone, create_embeddings_batch
from utils.text_utils import chunk_text

logger = get_logger('training_service')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_INDEX_HOST = os.environ.get('PINECONE_INDEX_HOST', '')

def extract_json_from_text(text: str) -> Any:
    """Robustly extract JSON from text that might contain markdown or extra commentary."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    text = text.strip()
    
    # Try markdown code blocks first (most specific)
    import re
    # Match ```json { ... } ``` or ``` { ... } ```
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the outermost JSON object
    # We find the first { and the last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # If that fails, it might be that there are multiple objects or noise
            # Try a stricter regex for just the first object if the simple slice failed
            pass
            
    raise ValueError("Could not extract valid JSON from response")

def build_category_embedding_prompt(category: str) -> str:
    return f"Summarize key facts, procedures, and scenarios for training category: {category}"

def aggregate_category_content(category: str, top_k: int = None, course_id: int = 1) -> str:
    if top_k is None:
        top_k = db.get_system_setting('rag_top_k', 50)
        
    try:
        # Create embedding for the category prompt
        # Set a short timeout for this operation if possible, or wrap in try/except
        embedding = create_embeddings_batch([build_category_embedding_prompt(category)])[0]
    except Exception as e:
        logger.error(f"Failed to create category embedding: {e}")
        embedding = None
    
    if not embedding:
        return ""

    text_chunks: List[str] = []
    try:
        # Use pinecone service to query
        results = query_pinecone(embedding, category, top_k=top_k, course_id=course_id)
        
        # Collect metadata text
        for m in results:
            meta = m.get('metadata', {}) or {}
            txt = meta.get('text')
            video = meta.get('video_name', 'Unknown')
            if txt:
                # distinct source marker for LLM
                text_chunks.append(f"SOURCE: {video}\nCONTENT: {txt}")
    except Exception as e:
        logger.error(f"Failed to aggregate category content: {e}")
    
    combined = "\n\n".join(text_chunks)
    return combined[:20000]

def build_answer_rag_context(category: str, user_answer: str, top_k: int = 5, course_id: int = 1) -> str:
    """
    Build RAG context specifically for a user's answer by:
    - Embedding the answer
    - Querying Pinecone with that embedding within the category namespaces
    - Joining top_k chunk texts
    Fallbacks to aggregate_category_content if anything fails.
    """
    try:
        # Embed user answer
        embedding = create_embeddings_batch([user_answer])[0]

        # Query Pinecone using same namespaces as question generation
        # We can reuse query_pinecone from service
        matches = query_pinecone(embedding, category, top_k=top_k, course_id=course_id)
        
        texts: List[str] = []
        for m in matches:
            txt = (m.get('metadata') or {}).get('text')
            if txt:
                texts.append(txt)
                
        if not texts:
            return aggregate_category_content(category, top_k=top_k, course_id=course_id)
            
        combined = "\n\n".join(texts)
        return combined[:20000]
    except Exception as e:
        logger.error(f"Answer RAG context build failed: {e}")
        return aggregate_category_content(category, top_k=top_k, course_id=course_id)

def determine_adaptive_difficulty(user_id: int, category: str, course_id: int = 1) -> str:
    """
    Determine difficulty based on user's past performance in the category.
    """
    try:
        # Get last 5 completed sessions for this category
        sessions = db.get_user_sessions(user_id, course_id=course_id)
        cat_sessions = [s for s in sessions 
                        if s.get('category') == category 
                        and s.get('status') == 'completed'
                        and s.get('overall_score') is not None]
        
        # Sort by date desc
        cat_sessions.sort(key=lambda x: x.get('started_at') or '', reverse=True)
        recent = cat_sessions[:5]
        
        if not recent:
            return 'trial' # Start with trial if no history
            
        avg_score = sum(s['overall_score'] for s in recent) / len(recent)
        
        if avg_score < 6.0:
            return 'trial'
        elif avg_score < 8.0:
            return 'basics'
        else:
            return 'field-ready'
            
    except Exception as e:
        logger.error(f"Error determining adaptive difficulty: {e}")
        return 'basics'

def prepare_questions(session_id: int, category: str, difficulty: str, duration_minutes: int = 10, mode: str = 'standard', course_id: int = 1) -> Dict:
    """
    Prepare questions for a session using LLM and RAG.
    Replaces prepare_questions_internal_v3
    """
    # Fetch System Settings
    q_per_min = db.get_system_setting('questions_per_min', 0.6)
    abs_min = db.get_system_setting('min_questions', 7)
    abs_max = db.get_system_setting('max_questions', 25)
    gen_source = db.get_system_setting('generate_source', 'default')
    llm_model = db.get_system_setting('llm_model', 'openai/gpt-4o')
    temp_questions = db.get_system_setting('temperature_questions', 0.7)
    rag_top_k = db.get_system_setting('rag_top_k', 50)

    # Base minimum counts by difficulty
    min_counts = {
        'trial': abs_min,
        'basics': abs_min + 1,
        'field-ready': abs_min + 2
    }
    
    # Handle Adaptive Difficulty
    if (difficulty or '').lower() in ['adaptive', 'auto']:
        # We need the user_id to calculate adaptive difficulty. 
        # Since prepare_questions doesn't strictly require user_id in signature (it takes session_id),
        # we need to fetch user_id from session.
        try:
            session_data = db.get_session(session_id)
            if session_data and session_data.get('user_id'):
                difficulty = determine_adaptive_difficulty(session_data['user_id'], category, course_id=course_id)
                logger.info(f"Adaptive difficulty determined: {difficulty} for user {session_data['user_id']}")
            else:
                difficulty = 'basics'
        except Exception as e:
            logger.error(f"Failed to determine adaptive difficulty: {e}")
            difficulty = 'basics'

    dl = (difficulty or '').lower()
    base_min = min_counts.get(dl, abs_min)
    
    # Dynamic Calculation
    calculated_count = int(duration_minutes * q_per_min)
    
    # Use max of base_min or calculated, cap at abs_max
    num_questions = min(max(calculated_count, base_min), abs_max)
    
    logger.info(f"Preparing {num_questions} questions for {duration_minutes} min session (difficulty: {difficulty}, mode: {mode})")

    # Get recent questions to avoid duplication
    recent_questions = []
    try:
        session_data = db.get_session(session_id)
        if session_data and session_data.get('user_id'):
            recent_questions = db.get_recent_questions(session_data['user_id'], category, limit=50, course_id=course_id)
    except Exception as e:
        logger.error(f"Failed to fetch recent questions: {e}")

    is_objection_category = 'objection' in (category or '').lower()
    if gen_source == 'rag_only':
        try:
            t0 = datetime.now()
            prompts = [
                f"facts about {category}",
                f"procedures for {category}",
                f"scenarios in {category}"
            ]
            embeddings = create_embeddings_batch(prompts)
            matches = []
            for emb in embeddings:
                m = query_pinecone(emb, category, top_k=100, course_id=course_id)
                matches.extend(m or [])
            texts = []
            for m in matches:
                meta = m.get('metadata') or {}
                txt = meta.get('text') or ''
                video = meta.get('video_name') or 'Unknown'
                if txt and len(txt) > 40:
                    texts.append((txt, video))
            def split_sentences(text: str) -> List[str]:
                import re
                s = re.split(r'(?<=[\\.\\?!])\\s+', text.strip())
                return [x.strip() for x in s if 40 <= len(x.strip()) <= 240]
            stop = set(['the','and','or','a','an','of','for','to','in','on','with','by','is','are','was','were','be','as','at','from','that','this','it'])
            def key_points_for(s: str) -> List[str]:
                words = [w.strip(',.!?').lower() for w in s.split()]
                uniq = []
                for w in words:
                    if w.isalpha() and w not in stop and w not in uniq:
                        uniq.append(w)
                return uniq[:3]
            generated = []
            for txt, video in texts:
                for sent in split_sentences(txt):
                    qtype = 'factual'
                    ls = sent.lower()
                    if any(k in ls for k in ['steps','procedure','how to','first','then','next']):
                        qtype = 'procedural'
                    elif any(k in ls for k in ['scenario','what if','handle','customer says','deal with']):
                        qtype = 'scenario'
                    is_obj = any(k in ls for k in ['objection','price','budget','looks fake','concern','hesitate'])
                    q = {
                        'question': {
                            'factual': f"What does the training say about: {sent[:80]}?",
                            'procedural': f"Describe the correct procedure related to: {sent[:80]}",
                            'scenario': f"How would you handle this scenario: {sent[:100]}"
                        }[qtype],
                        'expected_answer': sent,
                        'key_points': key_points_for(sent),
                        'source': video,
                        'difficulty': difficulty,
                        'is_objection': is_obj
                    }
                    generated.append(q)
                    if len(generated) >= num_questions * 2:
                        break
                if len(generated) >= num_questions * 2:
                    break
            seen = set([rq.lower() for rq in recent_questions])
            dedup = []
            for q in generated:
                qt = (q.get('question') or '').lower()
                if qt and qt not in seen:
                    dedup.append(q)
                if len(dedup) >= num_questions:
                    break
            if not dedup:
                logger.warning("RAG-only generation produced no questions")
                dedup = generated[:num_questions]
            db.save_prepared_questions(session_id, dedup)
            stored = db.get_session_questions(session_id)
            logger.info(f"rag_only_generation_ms={int((datetime.now()-t0).total_seconds()*1000)} category={category} count={len(stored)}")
            return {'questions': stored}
        except Exception as e:
            logger.error(f"RAG-only generation failed: {e}", exc_info=True)

    distribution_hint = {
        'trial': 'Mostly factual (approx 70%) with some procedural (approx 30%); no complex scenarios',
        'basics': 'Balanced mix of factual (40%), procedural (30%), and scenario (30%) questions',
        'field-ready': 'Focus on procedural (30%) and complex scenario/edge-case (70%) questions. INCLUDE MULTI-TURN SCENARIOS.'
    }.get(dl, 'balanced mix of factual, procedural, and scenario questions')
    
    objection_hint = ''
    if is_objection_category:
        objection_hint = (
            "\nOBJECTION SCENARIOS TO COVER (mark is_objection=true):\n"
            "- Longevity vs natural look tradeoff\n"
            "- Budget below ₹35,000 (two-option framing)\n"
            "- Why not transplant? (donor limitations and density)\n"
            "- Proper closing technique after handling objections\n"
            "- Indecisive customer (remove pressure, maintain authority)\n"
        )
    
    scenario_instruction = ""
    if dl == 'field-ready' or mode == 'exam':
        scenario_instruction = (
            "\nMULTI-TURN SCENARIO INSTRUCTION:\n"
            "- Generate at least one 'Scenario Chain' of 2-3 connected questions.\n"
            "- Question N: Sets up a situation.\n"
            "- Question N+1: 'Continuing from the previous scenario, the customer now says...'\n"
            "- This simulates a back-and-forth conversation.\n"
        )
    
    # Exam Mode Instructions
    exam_instruction = ""
    if mode == 'exam':
        exam_instruction = (
            "\nCERTIFICATION EXAM MODE:\n"
            "- Questions must be challenging and test deep understanding.\n"
            "- Include critical edge cases.\n"
            "- Do NOT simplify language; use professional terminology.\n"
        )

    content = aggregate_category_content(category, top_k=rag_top_k, course_id=course_id)
    if not content or len(content) < 50:
        training_material_section = f"NOTE: Specific training material unavailable. Use your expert knowledge about '{category}' in a high-ticket sales context."
        strict_rule_1 = "1) Every question must be answerable from the provided context if available. Otherwise, use conservative knowledge."
    else:
        training_material_section = f"TRAINING MATERIAL (verbatim excerpts; do not invent facts):\n{content[:8000]}"
        strict_rule_1 = "1) Every question must be answerable from the material. No outside knowledge."

    system_prompt = f"""You are an expert sales training coach creating exam questions.

{training_material_section}

TASK: Generate exactly {num_questions} questions to test knowledge of "{category}".

{f'''AVOID REPEATING THESE RECENTLY ASKED QUESTIONS:
{chr(10).join(['- ' + q[:100] + '...' for q in recent_questions[:20]])}
''' if recent_questions else ''}

QUESTION MIX for difficulty "{difficulty}":
- Order questions from EASIEST to HARDEST (Progressive Difficulty).
- {distribution_hint}
{objection_hint}
{scenario_instruction}
{exam_instruction}

STRICT RULES:
{strict_rule_1}
2) Provide an "expected_answer".
3) Provide 3-5 "key_points" the answer should include (short phrases).
4) Provide a "source" reference (use "General Knowledge" or specific video name if available).
5) Phrase questions like a real customer would ask.
6) Set "is_objection"=true only for objection-handling technique questions.
7) Include a "difficulty" field matching the input difficulty.

OUTPUT (JSON only):
{{
  "questions": [
    {{
      "question": "...",
      "expected_answer": "...",
      "key_points": ["a","b","c"],
      "source": "...",
      "difficulty": "{difficulty}",
      "is_objection": false
    }}
  ]
}}"""
    try:
        t0 = datetime.now()
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'AHL Sales Trainer'
            },
            json={
                'model': llm_model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'Generate {num_questions} exam questions for {category} at {difficulty} level.'}
                ],
                'temperature': temp_questions,
                'max_tokens': min(300 + num_questions * 150, 4500)
            },
            timeout=45
        )
        response.raise_for_status()
        result = response.json()
        content_response = result['choices'][0]['message']['content']
        
        try:
            data = extract_json_from_text(content_response)
        except ValueError:
            logger.warning("JSON extraction failed in prepare_questions, trying simple cleanup")
            # Fallback simple cleanup if the robust extractor fails (unlikely but safe)
            if '```json' in content_response:
                content_response = content_response.split('```json')[1].split('```')[0]
            elif '```' in content_response:
                content_response = content_response.split('```')[1].split('```')[0]
            data = json.loads(content_response.strip())
            
        questions = data.get('questions', [])
        logger.info(f"question_generation_duration_ms={int((datetime.now()-t0).total_seconds()*1000)} category={category} difficulty={difficulty}")
    except Exception as e:
        logger.error(f"Question generation failed: {e}", exc_info=True)
        # Fallback questions to keep training flow working offline
        base = [
            {
                'question': 'How often should the system be serviced?',
                'expected_answer': 'Every 3-4 weeks for cleaning and re-bonding.',
                'key_points': ['3-4 weeks', 'hygiene', 're-bonding'],
                'source': 'General Knowledge',
                'difficulty': difficulty,
                'is_objection': False
            },
            {
                'question': 'Why is a hair system better than a transplant for immediate results?',
                'expected_answer': 'Transplants take months to grow and depend on donor area; systems are instant and guarantee density.',
                'key_points': ['instant results', 'guaranteed density', 'no donor limit'],
                'source': 'General Knowledge',
                'difficulty': difficulty,
                'is_objection': True
            },
            {
                'question': 'What determines the lifespan of a hair patch?',
                'expected_answer': 'The base material (thin skin vs monofilament) and care routine.',
                'key_points': ['base material', 'care routine', 'thickness'],
                'source': 'General Knowledge',
                'difficulty': difficulty,
                'is_objection': False
            },
            {
                'question': 'How do you handle a customer who says "It looks fake"?',
                'expected_answer': 'Acknowledge concern, show before/afters, explain hairline technology.',
                'key_points': ['validate', 'social proof', 'technology'],
                'source': 'General Knowledge',
                'difficulty': difficulty,
                'is_objection': True
            },
            {
                'question': 'What is the price range for a standard system?',
                'expected_answer': 'Varies by quality, typically 15k to 50k depending on base and hair type.',
                'key_points': ['15k-50k', 'quality dependent'],
                'source': 'General Knowledge',
                'difficulty': difficulty,
                'is_objection': False
            }
        ]
        # Repeat/trim to desired count
        questions = (base * ((num_questions // len(base)) + 1))[:num_questions]
    
    try:
        db.save_prepared_questions(session_id, questions)
        stored = db.get_session_questions(session_id)
    except Exception as e:
        logger.error(f"Saving prepared questions failed: {e}")
        stored = []
    return {'questions': stored}

import math

def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

def evaluate_answer(session_id: int, question: Dict, user_answer: str, category: str, course_id: int = 1) -> Dict:
    """
    Evaluate a user's answer against the question and training material.
    Includes fuzzy match fallback using embeddings.
    """
    # Fetch Settings
    llm_model = db.get_system_setting('llm_model', 'openai/gpt-4o')
    temp_eval = db.get_system_setting('temperature_eval', 0.3)
    max_tokens = db.get_system_setting('max_tokens_answer', 1000)

    # Build evaluation prompt (objection vs standard)
    key_points = json.loads(question.get('key_points_json') or '[]')
    is_objection = bool(question.get('is_objection'))
    training_content = build_answer_rag_context(category, user_answer, top_k=5, course_id=course_id)
    
    # Fetch session mode
    try:
        sess = db.get_session(session_id)
        mode = sess.get('mode', 'standard')
    except:
        mode = 'standard'
        
    is_exam = mode == 'exam'
    
    if is_objection:
        forbidden = [
            'apologizing for price/limitations',
            'arguing with customer',
            'over-explaining',
            'losing control of conversation'
        ]
        forbidden_str = "\n".join([f"- {m}" for m in forbidden])
        
        # Exam mode prompt adjustment
        role_description = "You are a STRICT CERTIFICATION EXAMINER." if is_exam else "You are evaluating a sales trainee's objection-handling response."
        score_instruction = "Penalize ambiguity and lack of confidence heavily." if is_exam else "If the core meaning matches: Minimum Score = 7/10"
        
        evaluation_prompt = f"""{role_description}
EVALUATION CRITERIA:
- IGNORE filler words (um, uh, like, you know) and minor stammering.
- Focus strictly on MEANING and INTENT.
- Paraphrasing is ENCOURAGED. If they convey the right concept in different words, give FULL CREDIT.
- Do not penalize for conversational style or informal grammar.
- **CRITICAL**: If the user's answer is short but correct, score it HIGH (8/10+). Do not punish brevity if the point is made.
- **SYNONYMS**: Recognize synonyms (e.g. "expensive" == "costly", "trust" == "confidence").

SCORING RULES:
- {score_instruction}
- If technique is correct but wording is different: Score = 8/10 or higher
- Only penalize if they explicitly violate a Forbidden Mistake or give factually wrong info.

FEEDBACK GUIDELINES:
- Start with what they did RIGHT (e.g., "Good job staying calm").
- If they paraphrased correctly, acknowledge it (e.g., "You captured the right idea about...").
- Keep criticism constructive and focused on major missing points, not minor word choices.

PENALTIES: apologizing (-3), arguing (-5), over-explaining (-2), losing control (-4)
BONUS: using prescribed language OR equivalent professional phrasing (+2)

OBJECTION SCENARIO:
{question.get('question_text')}

EXPECTED (from training):
{question.get('expected_answer')}

KEY POINTS:
{json.dumps(key_points, indent=2)}

FORBIDDEN MISTAKES:
{forbidden_str}

RELEVANT TRAINING CONTENT:
{training_content[:1500]}

USER'S ANSWER:
"{user_answer}"

OUTPUT JSON:
{{
  "tone": 0,
  "technique": 0,
  "key_points_covered": 0,
  "closing": 0,
  "objection_score": 0,
  "overall_score": 0,
  "what_correct": "",
  "what_missed": "",
  "what_wrong": null,
  "forbidden_mistakes_made": [],
  "prescribed_language_used": false,
  "feedback": "",
  "spoken_feedback": "Short, encouraging, specific 1-2 sentences for TTS",
  "evidence_from_training": ""
}}"""
    else:
        role_description = "You are a STRICT CERTIFICATION EXAMINER." if is_exam else "You are a supportive sales training evaluator."
        goal_description = "Your goal is to verify deep understanding and precision." if is_exam else "Your goal is to verify understanding, not memorization."
        
        evaluation_prompt = f"""{role_description}
{goal_description}

IMPORTANT INSTRUCTIONS:
1. IGNORE filler words, hesitations, or conversational fluff.
2. If the user captures the CORE IDEA, mark it correct (8/10+).
3. Do NOT penalize for using different vocabulary if the meaning is preserved.
4. Example: If expected is "Build trust", and user says "Make them feel comfortable", count it as CORRECT.
5. **CRITICAL**: If the user's answer is short but correct, score it HIGH. Do not punish brevity.
6. **SYNONYMS**: Recognize synonyms (e.g. "client" == "customer", "verify" == "check").

SCORING GUIDANCE:
- Semantically correct but informal: 8/10
- Covers key points with fillers: 9/10
- Factually wrong: <5/10

FEEDBACK GUIDELINES:
- If the answer is correct but informal, praise the understanding (e.g., "Spot on! You understood that...").
- Do NOT correct their grammar or word choice unless it changes the meaning.
- Keep spoken_feedback conversational and encouraging.

QUESTION:
{question.get('question_text')}

EXPECTED ANSWER:
{question.get('expected_answer')}

KEY POINTS:
{json.dumps(key_points, indent=2)}

RELEVANT TRAINING MATERIAL:
{training_content[:1500]}

USER'S ANSWER:
"{user_answer}"

OUTPUT JSON:
{{
  "accuracy": 0,
  "completeness": 0,
  "clarity": 0,
  "overall_score": 0,
  "what_correct": "",
  "what_missed": "",
  "what_wrong": null,
  "feedback": "",
  "spoken_feedback": "Short, encouraging, specific 1-2 sentences for TTS",
  "evidence_from_training": ""
}}"""
    try:
        t0 = datetime.now()
        eval_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'AHL Sales Trainer'
            },
            json={
                'model': llm_model,
                'messages': [
                    {'role': 'system', 'content': evaluation_prompt},
                    {'role': 'user', 'content': 'Evaluate this answer strictly but fairly.'}
                ],
                'temperature': temp_eval,
                'max_tokens': max_tokens
            },
            timeout=30
        )
        eval_response.raise_for_status()
        result = eval_response.json()
        content = result['choices'][0]['message']['content']
        
        # Robust JSON extraction
        try:
            evaluation = extract_json_from_text(content)
        except Exception as e:
            logger.warning(f"JSON extraction failed in evaluate_answer: {e}. Content: {content[:200]}...")
            # Last resort fallback if extract_json_from_text fails
            if '```json' in content:
                clean_content = content.split('```json')[1].split('```')[0].strip()
                evaluation = json.loads(clean_content)
            elif '```' in content:
                clean_content = content.split('```')[1].split('```')[0].strip()
                evaluation = json.loads(clean_content)
            else:
                raise ValueError("No JSON object found in response")

        logger.info(f"evaluation_duration_ms={int((datetime.now()-t0).total_seconds()*1000)} category={category} is_objection={is_objection}")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}. Content was: {content if 'content' in locals() else 'No content'}", exc_info=True)
        evaluation = {
            'accuracy': None, 'completeness': None, 'clarity': None,
            'tone': None, 'technique': None, 'closing': None,
            'overall_score': 0, 'feedback': 'Evaluation failed due to technical error', 'evidence_from_training': '',
        }
    
    evaluation['user_answer'] = user_answer

    # --- FUZZY MATCH & KEYWORD FALLBACK ---
    # If LLM score is low (< 5), check semantic similarity and keywords
    try:
        raw_score = float(evaluation.get('overall_score') or 0)
        if raw_score < 5.0 and user_answer.strip():
            logger.info("Low LLM score detected, attempting fallbacks...")
            
            # 1. Keyword Check
            matched_keywords = []
            ua_lower = user_answer.lower()
            for kp in key_points:
                if kp.lower() in ua_lower:
                    matched_keywords.append(kp)
            
            keyword_ratio = len(matched_keywords) / len(key_points) if key_points else 0
            logger.info(f"Keyword match ratio: {keyword_ratio:.2f} ({len(matched_keywords)}/{len(key_points)})")

            if keyword_ratio >= 0.5:
                 logger.info("High keyword overlap detected! Overriding score to 6.5")
                 evaluation['overall_score'] = max(float(evaluation.get('overall_score') or 0), 6.5)
                 evaluation['accuracy'] = 6.5
                 evaluation['feedback'] = f"You mentioned key points like '{', '.join(matched_keywords[:2])}'. Good job hitting the main concepts."
                 evaluation['spoken_feedback'] = "You hit the main keywords. Good job."
                 evaluation['what_correct'] = "Included majority of key points."
                 # Don't return yet, let fuzzy match potentially boost it higher

            # 2. Semantic Similarity Check
            expected = question.get('expected_answer', '')
            if expected:
                # Generate embeddings for both
                embeddings = create_embeddings_batch([user_answer, expected])
                if len(embeddings) == 2:
                    similarity = calculate_cosine_similarity(embeddings[0], embeddings[1])
                    logger.info(f"Fuzzy match similarity: {similarity:.4f}")
                    
                    if similarity > 0.80:
                        logger.info("High similarity detected! Overriding score to 8.0")
                        evaluation['overall_score'] = 8.0
                        evaluation['accuracy'] = 8.0
                        evaluation['completeness'] = 7.0 # slightly lower as it might be brief
                        evaluation['feedback'] = "Your answer matches the expected meaning very closely. Good job!"
                        evaluation['spoken_feedback'] = "That's correct! You got the core meaning right."
                        evaluation['what_correct'] = "Core meaning matches expected answer (verified by semantic check)"
                    elif similarity > 0.65:
                         logger.info("Moderate similarity detected! Overriding score to 6.5")
                         # Only override if current score is lower
                         if float(evaluation.get('overall_score') or 0) < 6.5:
                             evaluation['overall_score'] = 6.5
                             evaluation['accuracy'] = 6.5
                             evaluation['feedback'] = "Your answer is on the right track, but could be more specific."
                             evaluation['spoken_feedback'] = "You're close, but try to be a bit more specific next time."
    except Exception as e:
        logger.error(f"Fallback checks failed: {e}")
    # ----------------------------

    # Ensure objection_score exists for objection questions
    if is_objection and 'objection_score' not in evaluation:
        try:
            evaluation['objection_score'] = float(evaluation.get('overall_score') or 0)
        except Exception:
            evaluation['objection_score'] = 0
    # Add a lightweight feedback tier and speakable feedback
    try:
        score = float(evaluation.get('overall_score') or 0)
    except Exception:
        score = 0.0
    if score >= 8:
        tier = 'positive'
        fallback_speak = 'Excellent! That is correct and well-articulated.'
    elif score >= 5:
        tier = 'constructive'
        fallback_speak = 'Good effort. You covered the main points, but you missed a few details.'
    else:
        tier = 'corrective'
        fallback_speak = 'Not quite. Please review the training material.'
        
    evaluation['feedback_tier'] = tier
    # Use LLM generated spoken feedback if available, otherwise fallback
    evaluation['speak_feedback'] = evaluation.get('spoken_feedback') or fallback_speak
    return evaluation
