# SigmaSight AI Training Process Guide

This document outlines the end-to-end process for training and fine-tuning your AI model, from data collection through deployment.

---

## Training Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: DATA COLLECTION                                        │
│  • Capture all user interactions                                │
│  • Collect feedback signals (ratings, edits, follow-ups)        │
│  • Duration: Ongoing                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: CURATION                                               │
│  • Review high-signal interactions weekly                       │
│  • Edit/improve responses as needed                             │
│  • Categorize and score examples                                │
│  • Target: 50-100 examples for first training                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: TRAINING                                               │
│  • Export JSONL training file                                   │
│  • Submit fine-tuning job to OpenAI                             │
│  • Wait ~30-60 minutes for completion                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: EVALUATION                                             │
│  • Test fine-tuned model on held-out examples                   │
│  • Compare against base model                                   │
│  • Check for regressions                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: DEPLOYMENT                                             │
│  • Deploy fine-tuned model to production                        │
│  • Monitor performance metrics                                  │
│  • Continue collecting data for next iteration                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Collection

### What to Capture

Every interaction should log:

| Field | Purpose |
|-------|---------|
| `user_message` | The input query |
| `assistant_response` | Model's output |
| `system_prompt` | Context given to model |
| `retrieved_context` | RAG documents used |
| `model_used` | Which model generated response |
| `feedback_rating` | User's thumbs up/down |
| `user_edited_response` | If user corrected output |
| `had_followup` | Did user ask clarifying question? |

### Feedback Signals (Ranked by Value)

1. **User edits** (highest value) - User corrected the response
2. **Explicit thumbs up** - User confirmed quality
3. **No follow-up needed** - User got what they needed
4. **Explicit thumbs down** - User flagged poor quality
5. **Follow-up question** - Response was incomplete/wrong

### Implementing Feedback Collection

**In your UI:**
```
┌─────────────────────────────────────────────────────────────┐
│  Q: What was NVDA's SBC in Q3?                               │
│                                                              │
│  A: NVIDIA's stock-based compensation in Q3 FY2025 was      │
│     $1.4B, representing 4.7% of revenue...                  │
│                                                              │
│  [👍] [👎] [✏️ Edit] [📋 Copy]                               │
└─────────────────────────────────────────────────────────────┘
```

**Edit flow:**
- When user clicks Edit, show the response in an editable textarea
- On save, store both original and edited version
- The edited version becomes the "gold standard" for training

---

## Phase 2: Curation

### Weekly Curation Workflow

**Step 1: Pull Candidates**

```sql
-- Get high-signal interactions from the past week
SELECT 
    id,
    user_message,
    assistant_response,
    user_edited_response,
    feedback_rating,
    created_at
FROM interaction_logs
WHERE 
    created_at > NOW() - INTERVAL '7 days'
    AND (
        feedback_rating = 1  -- thumbs up
        OR user_edited_response IS NOT NULL  -- user corrected
    )
    AND had_followup = FALSE
    AND id NOT IN (SELECT source_interaction_id FROM training_examples)
ORDER BY 
    CASE WHEN user_edited_response IS NOT NULL THEN 0 ELSE 1 END,
    created_at DESC;
```

**Step 2: Review Each Candidate**

For each interaction, ask:

1. ✅ Is the question representative of real user needs?
2. ✅ Is the response accurate and complete?
3. ✅ Does it follow our desired format/style?
4. ✅ Would this be a good example for the model to learn from?

**Step 3: Improve if Needed**

Before promoting, you may want to:

- Fix factual errors
- Improve formatting
- Add missing citations
- Remove unnecessary hedging
- Make the response more concise

**Step 4: Categorize**

Assign each example to a category:

| Category | Description |
|----------|-------------|
| `sec_10k` | 10-K annual report questions |
| `sec_10q` | 10-Q quarterly report questions |
| `sec_8k` | 8-K current report questions |
| `gaap_reconciliation` | GAAP vs non-GAAP questions |
| `sbc_breakdown` | Stock-based compensation questions |
| `analyst_estimates` | Analyst forecast questions |
| `financial_metrics` | Ratios, margins, growth rates |
| `comparison` | Multi-company comparisons |

**Step 5: Score Quality**

Rate 1-10:

| Score | Meaning |
|-------|---------|
| 9-10 | Exemplary - Model should definitely learn this |
| 7-8 | Good - Solid example |
| 5-6 | Acceptable - Usable but not ideal |
| 1-4 | Poor - Do not include |

### Curation Best Practices

**DO include examples that:**
- Cover edge cases
- Show proper citation format
- Demonstrate multi-step reasoning
- Handle ambiguous queries gracefully
- Admit uncertainty appropriately

**DON'T include examples that:**
- Have factual errors
- Are too generic (could be answered by base model)
- Contain hallucinated data
- Are overly verbose
- Don't match your desired output style

### Target Numbers

| Milestone | Examples | Expected Improvement |
|-----------|----------|---------------------|
| First training | 50-100 | Noticeable style/format consistency |
| Second iteration | 200-300 | Strong domain adaptation |
| Mature dataset | 500-1000+ | Near-expert performance |

---

## Phase 3: Training

### Pre-Training Checklist

- [ ] At least 50 approved examples (100+ preferred)
- [ ] Examples reviewed in past 2 weeks
- [ ] No duplicate or near-duplicate examples
- [ ] Balanced across categories (if possible)
- [ ] System prompt is finalized

### Training Data Format

OpenAI expects JSONL with this structure:

```json
{"messages": [{"role": "system", "content": "You are a financial analyst assistant..."}, {"role": "user", "content": "What was NVDA's revenue in Q3 2024?"}, {"role": "assistant", "content": "NVIDIA reported Q3 FY2025 revenue of $35.1B..."}]}
{"messages": [{"role": "system", "content": "You are a financial analyst assistant..."}, {"role": "user", "content": "Compare GOOGL's GAAP vs non-GAAP EPS"}, {"role": "assistant", "content": "For Q3 2024, Alphabet reported..."}]}
```

**Important:**
- Each line is a complete JSON object
- System prompt should be consistent across examples
- No trailing commas or extra whitespace
- UTF-8 encoding

### Submitting the Training Job

**Via API (recommended):**

```python
from openai import OpenAI
client = OpenAI()

# 1. Upload training file
with open("training_data.jsonl", "rb") as f:
    file = client.files.create(file=f, purpose="fine-tune")

print(f"File ID: {file.id}")

# 2. Create fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file.id,
    model="gpt-4o-mini-2024-07-18",
    hyperparameters={
        "n_epochs": 3  # 1-4 typical, "auto" also works
    },
    suffix="sigmasight-v1"  # Optional: custom model name suffix
)

print(f"Job ID: {job.id}")
print(f"Status: {job.status}")
```

**Via OpenAI Dashboard:**

1. Go to https://platform.openai.com/finetune
2. Click "Create"
3. Select base model (gpt-4o-mini-2024-07-18)
4. Upload your JSONL file
5. Configure hyperparameters
6. Start training

### Hyperparameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `n_epochs` | auto | Number of passes through data. 1-4 typical. |
| `batch_size` | auto | Samples per training step |
| `learning_rate_multiplier` | auto | How aggressively to update weights |

**Recommendations:**
- Start with defaults ("auto" for all)
- For small datasets (<100 examples), use 3-4 epochs
- For larger datasets (500+), use 1-2 epochs

### Monitoring Training

```python
# Check job status
job = client.fine_tuning.jobs.retrieve("ftjob-abc123")
print(f"Status: {job.status}")
print(f"Trained tokens: {job.trained_tokens}")

# List events
events = client.fine_tuning.jobs.list_events("ftjob-abc123", limit=10)
for event in events.data:
    print(f"{event.created_at}: {event.message}")
```

**Status values:**
- `validating_files` - Checking your data
- `queued` - Waiting to start
- `running` - Training in progress
- `succeeded` - Done! Model ready
- `failed` - Something went wrong

### Training Time Estimates

| Examples | Approximate Time |
|----------|-----------------|
| 50 | 15-20 minutes |
| 100 | 20-30 minutes |
| 500 | 45-60 minutes |
| 1000 | 1-2 hours |

### Cost Estimates

**GPT-4o-mini fine-tuning:**
- Training: $3.00 per 1M tokens
- Inference: $0.30/$1.20 per 1M input/output tokens

**Example calculation (100 examples, ~500 tokens each):**
```
Training tokens: 100 × 500 × 3 epochs = 150,000 tokens
Training cost: 150,000 / 1,000,000 × $3.00 = $0.45
```

---

## Phase 4: Evaluation

### Before Deploying

Never deploy without testing. Create an evaluation set of 20-50 examples that were NOT used in training.

### Evaluation Script

```python
import json
from openai import OpenAI

client = OpenAI()

def evaluate_model(model_id: str, eval_examples: list[dict]) -> dict:
    """
    Evaluate a model on held-out examples.
    Returns accuracy metrics.
    """
    results = []
    
    for example in eval_examples:
        # Get model response
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": example["system"]},
                {"role": "user", "content": example["user"]}
            ],
            temperature=0.3
        )
        
        predicted = response.choices[0].message.content
        expected = example["expected"]
        
        # Score (customize based on your criteria)
        score = score_response(predicted, expected, example)
        
        results.append({
            "query": example["user"],
            "expected": expected,
            "predicted": predicted,
            "score": score
        })
    
    return {
        "total": len(results),
        "avg_score": sum(r["score"] for r in results) / len(results),
        "results": results
    }

def score_response(predicted: str, expected: str, example: dict) -> float:
    """
    Score a response on 0-1 scale.
    Customize based on your needs.
    """
    score = 0.0
    
    # Check key facts are present
    key_facts = example.get("key_facts", [])
    facts_found = sum(1 for fact in key_facts if fact.lower() in predicted.lower())
    if key_facts:
        score += 0.5 * (facts_found / len(key_facts))
    
    # Check format compliance
    if example.get("expected_format"):
        # Add format checking logic
        pass
    
    # Check length is reasonable
    len_ratio = len(predicted) / len(expected)
    if 0.5 < len_ratio < 2.0:
        score += 0.3
    
    # Semantic similarity (optional, requires embeddings)
    # similarity = cosine_similarity(embed(predicted), embed(expected))
    # score += 0.2 * similarity
    
    return min(score, 1.0)

# Compare base vs fine-tuned
base_results = evaluate_model("gpt-4o-mini", eval_examples)
ft_results = evaluate_model("ft:gpt-4o-mini:...", eval_examples)

print(f"Base model avg score: {base_results['avg_score']:.2f}")
print(f"Fine-tuned avg score: {ft_results['avg_score']:.2f}")
```

### What to Check

| Aspect | Check For |
|--------|-----------|
| **Accuracy** | Are facts correct? |
| **Completeness** | Does it answer the full question? |
| **Format** | Does it match your desired style? |
| **Citations** | Are sources properly referenced? |
| **Conciseness** | Is it appropriately detailed? |
| **Regressions** | Did it get worse at anything? |

### A/B Testing in Production

If evaluation looks good, deploy with A/B testing:

```python
import random

def get_model_for_request(user_id: str) -> str:
    """Route users to base or fine-tuned model."""
    # 80% fine-tuned, 20% base (for comparison)
    if hash(user_id) % 100 < 80:
        return "ft:gpt-4o-mini:your-org::abc123"
    else:
        return "gpt-4o-mini"
```

Monitor:
- Response quality (feedback ratings)
- Latency
- Token usage
- User satisfaction

---

## Phase 5: Deployment & Iteration

### Deploying the Fine-Tuned Model

**Update your config:**

```python
# config.py
FINE_TUNED_MODEL_ID = "ft:gpt-4o-mini-2024-07-18:your-org::abc123"
```

**Or via environment variable:**

```bash
# Railway environment
FINE_TUNED_MODEL_ID=ft:gpt-4o-mini-2024-07-18:your-org::abc123
```

### Continuous Improvement Cycle

```
Week 1-4:    Collect interactions, gather feedback
Week 5:      Weekly curation session (30-60 min)
Week 6-8:    Continue collecting
Week 9:      Second curation session
Week 10:     Train new model version (v2)
Week 11:     Evaluate and deploy
Week 12+:    Repeat cycle
```

### Version Tracking

Keep track of your models:

| Version | Date | Examples | Base Model | Notes |
|---------|------|----------|------------|-------|
| v1 | 2025-01-15 | 87 | gpt-4o-mini | Initial training |
| v2 | 2025-02-15 | 203 | gpt-4o-mini | Added SBC examples |
| v3 | 2025-03-15 | 412 | gpt-4o-mini | Improved citations |

### When to Retrain

Retrain when you have:
- 50+ new quality examples since last training
- Noticed systematic errors in production
- Changed your system prompt significantly
- Added new categories of questions

### Handling Model Drift

Over time, your fine-tuned model might:
- Overfit to common query patterns
- Struggle with new types of questions
- Become stale as financial data changes

**Mitigations:**
- Always keep RAG layer active (fresh data)
- Include diverse examples in each training batch
- Periodically evaluate on new, unseen queries
- Consider ensemble: fine-tuned for common cases, base for edge cases

---

## Troubleshooting

### Common Issues

**Training job fails validation:**
- Check JSONL format (one object per line)
- Ensure all messages have role and content
- Check for empty strings or null values

**Model quality doesn't improve:**
- Examples may be too similar to what base model already knows
- Try more diverse/difficult examples
- Increase epochs (if underfitting)
- Decrease epochs (if overfitting)

**Model forgets base capabilities:**
- Include some general examples, not just domain-specific
- Reduce epochs
- Use larger base model

**Model outputs wrong format:**
- Include more examples with correct format
- Make format explicit in system prompt
- Use stronger formatting in examples

### Getting Help

- OpenAI fine-tuning guide: https://platform.openai.com/docs/guides/fine-tuning
- OpenAI Discord community
- Your feedback logs are your best diagnostic tool

---

## Quick Reference

### Commands

```bash
# Export training data
curl -X GET "https://your-api/admin/export/jsonl?min_quality=6" > training.jsonl

# Create fine-tuning job
curl -X POST "https://your-api/admin/fine-tune/create" \
  -H "Content-Type: application/json" \
  -d '{"base_model": "gpt-4o-mini-2024-07-18", "min_quality_score": 6}'

# Check job status
curl "https://your-api/admin/fine-tune/{job_id}/status"

# List models
curl "https://your-api/admin/fine-tune/models"
```

### Key Metrics to Track

| Metric | Target |
|--------|--------|
| Training examples | 100+ for first model |
| Curation rate | 10-20% of interactions promoted |
| Feedback collection | >30% of interactions have feedback |
| Model accuracy | >85% on eval set |
| Training frequency | Monthly |

### Cost Summary

| Activity | Cost |
|----------|------|
| Training (100 examples) | ~$0.50 |
| Training (500 examples) | ~$2.50 |
| Inference (1M tokens in) | $0.30 |
| Inference (1M tokens out) | $1.20 |

---

## Appendix: Example Training Data

### Good Example (SEC Filing Query)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a financial analyst assistant for SigmaSight, specializing in SEC filings, earnings analysis, and financial metrics. When answering questions: cite specific sources (10-K, 10-Q, 8-K filings), distinguish between GAAP and non-GAAP metrics, break down stock-based compensation by category, use precise numbers with appropriate units."
    },
    {
      "role": "user",
      "content": "What was NVIDIA's stock-based compensation in Q3 FY2025 and how does it break down by department?"
    },
    {
      "role": "assistant",
      "content": "According to NVIDIA's Q3 FY2025 10-Q filing, total stock-based compensation was $1.40 billion, representing 4.0% of revenue ($35.1B).\n\nBreakdown by function:\n- Cost of revenue: $47 million\n- Research and development: $941 million\n- Sales, general and administrative: $410 million\n\nR&D accounts for 67% of total SBC, reflecting NVIDIA's heavy investment in engineering talent for AI/GPU development. This is consistent with prior quarters and typical for semiconductor companies at NVIDIA's growth stage."
    }
  ]
}
```

### Good Example (GAAP vs Non-GAAP)

```json
{
  "messages": [
    {
      "role": "system", 
      "content": "You are a financial analyst assistant for SigmaSight..."
    },
    {
      "role": "user",
      "content": "Compare Amazon's GAAP and non-GAAP operating income for Q3 2024"
    },
    {
      "role": "assistant",
      "content": "From Amazon's Q3 2024 earnings (8-K filed October 31, 2024):\n\n**GAAP Operating Income:** $17.4 billion (11.0% margin)\n**Non-GAAP Operating Income:** $18.6 billion (11.8% margin)\n\nThe $1.2 billion difference consists of:\n- Stock-based compensation: $6.0 billion (added back)\n- Amortization of acquired intangibles: $0.3 billion (added back)\n- Other adjustments: -$5.1 billion (primarily one-time gains)\n\nNote: Amazon's non-GAAP adjustments are larger than most peers due to their significant SBC expense, which runs ~3.8% of revenue."
    }
  ]
}
```

### Good Example (Handling Uncertainty)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a financial analyst assistant for SigmaSight..."
    },
    {
      "role": "user",
      "content": "What will Apple's revenue be next quarter?"
    },
    {
      "role": "assistant",
      "content": "I can't predict future revenue with certainty, but I can share what analysts expect and Apple's guidance:\n\n**Analyst Consensus (Q1 FY2025):**\n- Revenue: $124.1 billion (range: $121.8B - $127.2B)\n- EPS: $2.35 (range: $2.28 - $2.42)\n\n**Apple's Guidance:**\nApple provided qualitative guidance suggesting 'low to mid single digit' revenue growth YoY, which would imply ~$121-125B.\n\n**Key Factors to Watch:**\n- iPhone 16 demand trajectory\n- China market performance\n- Services growth rate\n\nWould you like me to break down the segment-level estimates?"
    }
  ]
}
```
