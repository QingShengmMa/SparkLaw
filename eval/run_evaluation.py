"""Run offline evaluation with LLM-as-a-Judge and produce markdown report."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from langchain_core.messages import HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm_factory import LLMFactory
from app.core.logger import app_logger


JUDGE_PROMPT_TEMPLATE = """
你是严谨的法律问答评审官（LLM-as-a-Judge）。
请根据给定问题、参考答案、上下文、系统答案进行打分。

【评分维度】每项 1-5 分：
1) faithfulness: 回答是否基于上下文，是否有幻觉。
2) answer_relevance: 回答是否直接解决用户诉求。
3) format_adherence: 是否保持律师专业语气、结构清晰、Markdown 友好。

【输入】
Question:
{question}

Reference Answer:
{reference_answer}

Context (reference + retrieved):
{context}

System Answer:
{system_answer}

请严格输出 JSON，不要输出任何多余文字，结构如下：
{{
  "faithfulness": {{"score": 1-5, "reason": "..."}},
  "answer_relevance": {{"score": 1-5, "reason": "..."}},
  "format_adherence": {{"score": 1-5, "reason": "..."}},
  "overall": {{"score": 1-5, "reason": "..."}}
}}
""".strip()


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def call_legal_chat(api_base: str, question: str, session_id: str = "eval_session") -> str:
    url = f"{api_base.rstrip('/')}/api/legal/chat"
    payload = {"question": question, "session_id": session_id, "personality": "machine"}
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("answer", "")


def call_retrieve_context(api_base: str, question: str, top_k: int = 3) -> str:
    url = f"{api_base.rstrip('/')}/api/document/retrieve"
    payload = {"query": question, "top_k": top_k}
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        snippets = []
        for idx, item in enumerate(results, start=1):
            text = item.get("text", "")
            if text:
                snippets.append(f"[{idx}] {text[:300]}")
        return "\n".join(snippets)
    except Exception:
        return ""


def parse_judge_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("judge 输出不是 JSON")
    return json.loads(text[start : end + 1])


def judge_answer(judge_llm, question: str, reference_answer: str, context: str, system_answer: str) -> Dict[str, Any]:
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        reference_answer=reference_answer,
        context=context,
        system_answer=system_answer,
    )
    response = judge_llm.invoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    return parse_judge_json(content)


def to_float_score(judge_item: Dict[str, Any], key: str) -> float:
    val = judge_item.get(key, {}).get("score", 0)
    try:
        return float(val)
    except Exception:
        return 0.0


def render_report(results: List[Dict[str, Any]], output_path: Path) -> None:
    faithfulness_scores = [r["scores"]["faithfulness"] for r in results]
    relevance_scores = [r["scores"]["answer_relevance"] for r in results]
    format_scores = [r["scores"]["format_adherence"] for r in results]
    overall_scores = [r["scores"]["overall"] for r in results]

    bad_cases = [r for r in results if r["scores"]["overall"] <= 2 or r["scores"]["faithfulness"] <= 2]

    lines = [
        "# SparkLaw Offline Evaluation Report",
        "",
        f"- Generated at: {datetime.now().isoformat()}",
        f"- Sample size: {len(results)}",
        "",
        "## Average Scores (1-5)",
        "",
        f"- Faithfulness: **{statistics.mean(faithfulness_scores):.2f}**",
        f"- Answer Relevance: **{statistics.mean(relevance_scores):.2f}**",
        f"- Format Adherence: **{statistics.mean(format_scores):.2f}**",
        f"- Overall: **{statistics.mean(overall_scores):.2f}**",
        "",
        "## Bad Cases",
        "",
    ]

    if not bad_cases:
        lines.append("无明显低分案例。")
    else:
        for item in bad_cases:
            lines.extend(
                [
                    f"### {item['id']} ({item.get('category', 'N/A')})",
                    f"- Question: {item['question']}",
                    f"- System Answer: {item['system_answer']}",
                    f"- Scores: faithfulness={item['scores']['faithfulness']}, relevance={item['scores']['answer_relevance']}, format={item['scores']['format_adherence']}, overall={item['scores']['overall']}",
                    f"- Judge Overall Reason: {item['judge_raw'].get('overall', {}).get('reason', '')}",
                    "",
                ]
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SparkLaw offline evaluation baseline")
    parser.add_argument("--dataset", type=str, default=str(PROJECT_ROOT / "eval" / "eval_dataset.jsonl"))
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--judge-model", type=str, default="gpt-4o")
    parser.add_argument("--output", type=str, default=str(PROJECT_ROOT / "eval" / "reports" / "evaluation_report.md"))
    args = parser.parse_args()

    dataset = load_jsonl(Path(args.dataset))
    judge_llm = LLMFactory.create_llm(model=args.judge_model, temperature=0.0, max_tokens=1200)

    all_results: List[Dict[str, Any]] = []

    for i, row in enumerate(dataset, start=1):
        question = row["question"]
        reference_answer = row.get("reference_answer", "")
        reference_context = row.get("reference_context", "")

        app_logger.info(f"[{i}/{len(dataset)}] evaluating: {row.get('id', i)}")

        system_answer = call_legal_chat(args.api_base, question, session_id="eval_session")
        retrieved_context = call_retrieve_context(args.api_base, question, top_k=3)
        full_context = (reference_context + "\n" + retrieved_context).strip()

        judge_raw = judge_answer(
            judge_llm=judge_llm,
            question=question,
            reference_answer=reference_answer,
            context=full_context,
            system_answer=system_answer,
        )

        scores = {
            "faithfulness": to_float_score(judge_raw, "faithfulness"),
            "answer_relevance": to_float_score(judge_raw, "answer_relevance"),
            "format_adherence": to_float_score(judge_raw, "format_adherence"),
            "overall": to_float_score(judge_raw, "overall"),
        }

        all_results.append(
            {
                "id": row.get("id", f"eval_{i:03d}"),
                "category": row.get("category", "N/A"),
                "question": question,
                "reference_answer": reference_answer,
                "system_answer": system_answer,
                "scores": scores,
                "judge_raw": judge_raw,
            }
        )

    report_path = Path(args.output)
    render_report(all_results, report_path)

    detail_json = report_path.with_suffix(".json")
    detail_json.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Evaluation completed.\nReport: {report_path}\nDetails: {detail_json}")


if __name__ == "__main__":
    main()
