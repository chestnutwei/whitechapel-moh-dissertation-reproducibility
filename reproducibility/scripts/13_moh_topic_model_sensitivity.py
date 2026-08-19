"""Primary deterministic NMF plus random-initialisation sensitivity checks.

The analysis deliberately excludes a small, fixed list of title-page/front-matter
passages recorded in data/metadata/topic_model_exclusions.csv. Keyword retrieval
continues to use all 275 narrative passages; this script therefore records its
smaller input set explicitly in topic_model_input.csv.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "outputs" / "tables"
TECH = TABLES / "technical"
OUTPUT_AUDIT = PROJECT_ROOT / "outputs" / "audit"
PASSAGES = TABLES / "moh_narrative_passages.csv"
EXCLUSIONS = PROJECT_ROOT / "data" / "metadata" / "topic_model_exclusions.csv"

K_VALUES = [4, 5, 6, 7, 8]
SEEDS = [1, 21, 42, 84, 100]
TOP_N = 12
PRIMARY_K = 7
PRIMARY_INIT = "nndsvda"
PRIMARY_MAX_ITER = 1500
PRIMARY_TOL = 1e-5


def preprocess_text(text: str) -> str:
    text = str(text).lower().replace("&", " and ")
    # Topic modelling tokenisation treats hyphens as word separators. This is
    # distinct from the frozen dictionary's limited lexical-normalisation layer.
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_rows(a: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(a, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return a / norms


def match_components(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sim = cosine_similarity(normalise_rows(a), normalise_rows(b))
    rows, cols = linear_sum_assignment(-sim)
    order = np.argsort(rows)
    rows, cols = rows[order], cols[order]
    scores = sim[rows, cols]
    return cols, scores, sim


def top_terms(components: np.ndarray, features: np.ndarray, n: int = TOP_N) -> list[list[str]]:
    out = []
    for topic in components:
        idx = np.argsort(topic)[::-1][:n]
        out.append(features[idx].tolist())
    return out


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


def main() -> None:
    TECH.mkdir(parents=True, exist_ok=True)
    OUTPUT_AUDIT.mkdir(parents=True, exist_ok=True)
    passages = pd.read_csv(PASSAGES)
    narrative = passages[passages["likely_narrative"] == True].copy()
    exclusions = pd.read_csv(EXCLUSIONS)
    exclusion_map = dict(zip(exclusions["passage_id"], exclusions["reason"]))

    narrative["topic_model_excluded"] = narrative["passage_id"].isin(exclusion_map)
    narrative["topic_model_exclusion_reason"] = narrative["passage_id"].map(exclusion_map).fillna("")
    narrative["topic_model_text"] = narrative["passage_text"].map(preprocess_text)
    narrative[["report_year", "passage_id", "word_count", "topic_model_excluded", "topic_model_exclusion_reason", "topic_model_text"]].to_csv(
        TECH / "topic_model_input.csv", index=False
    )

    model_df = narrative[~narrative["topic_model_excluded"]].copy().reset_index(drop=True)
    vectorizer = TfidfVectorizer(
        stop_words="english",
        min_df=2,
        max_df=0.90,
        ngram_range=(1, 2),
        max_features=4000,
        sublinear_tf=True,
    )
    X = vectorizer.fit_transform(model_df["topic_model_text"])
    features = np.array(vectorizer.get_feature_names_out())

    all_models: dict[tuple[int, int], dict] = {}
    summary_rows = []

    # Primary solution: deterministic initialisation stabilises component
    # identity across BLAS implementations. Floating-point weights can still
    # differ slightly, so cross-platform validation compares terms and values
    # with documented tolerances rather than byte hashes.
    primary_model = NMF(
        n_components=PRIMARY_K,
        init=PRIMARY_INIT,
        random_state=0,
        max_iter=PRIMARY_MAX_ITER,
        solver="cd",
        beta_loss="frobenius",
        tol=PRIMARY_TOL,
    )
    primary_W = primary_model.fit_transform(X)
    primary_H = primary_model.components_
    primary_terms = top_terms(primary_H, features)
    pd.DataFrame([
        {"topic": topic, "top_terms": "; ".join(terms)}
        for topic, terms in enumerate(primary_terms, start=1)
    ]).to_csv(TECH / "nmf_primary_topics_k7.csv", index=False)
    primary_scores = model_df[["report_year", "passage_id", "word_count"]].copy()
    for topic in range(PRIMARY_K):
        primary_scores[f"topic_{topic + 1}"] = primary_W[:, topic]
    primary_scores["dominant_topic"] = primary_W.argmax(axis=1) + 1
    primary_scores["dominant_weight"] = primary_W.max(axis=1)
    primary_scores.to_csv(TECH / "nmf_primary_document_topics_k7.csv", index=False)
    np.save(TECH / "nmf_primary_components_k7.npy", primary_H)

    # Assign the five documented interpretive labels once from the primary
    # deterministic terms. This is a strict primary-model gate and is wholly
    # independent of random-start recovery.
    interpretations = [
        ("Address-specific enforcement proceedings", ("street", "summons", "withdrawn", "workshop")),
        ("Sanitary authority, statutory penalties and legal powers", ("authority", "sanitary authority", "section", "notice")),
        ("Housing reform and metropolitan governance", ("houses", "district", "council", "county council")),
        ("Sanitary construction regulations", ("construct", "receptacle", "watercloset", "privy")),
        ("Penalty and by-law clauses", ("penalty", "offence", "bye laws", "foregoing bye")),
    ]
    term_sets = [set(terms) for terms in primary_terms]
    score_matrix = np.array([
        [sum(term in words for term in required) for words in term_sets]
        for _label, required in interpretations
    ], dtype=float)
    label_rows, topic_cols = linear_sum_assignment(-score_matrix)
    assigned = dict(zip(label_rows.tolist(), topic_cols.tolist()))
    assignment_rows = []
    for label_idx, (label, _required) in enumerate(interpretations):
        col = assigned[label_idx]
        score = float(score_matrix[label_idx, col])
        alternatives = sorted(
            ((float(score_matrix[label_idx, other]), other + 1) for other in range(PRIMARY_K) if other != col),
            reverse=True,
        )
        second_score, second_topic = alternatives[0]
        margin = score - second_score
        status = "assigned" if score >= 3 and margin >= 1 else "ambiguous"
        assignment_rows.append({
            "interpretive_label": label, "topic_id": col + 1, "score": score,
            "top_terms": "; ".join(primary_terms[col]), "second_best_topic": second_topic,
            "second_best_score": second_score, "assignment_margin": margin,
            "status": status,
            "notes": "Global one-to-one assignment from deterministic primary terms; random sensitivity is not consulted.",
        })
    assignment_df = pd.DataFrame(assignment_rows)
    assignment_df.to_csv(TECH / "nmf_component_assignment.csv", index=False)
    assignment_df.to_csv(OUTPUT_AUDIT / "nmf_component_assignment.csv", index=False)
    if (assignment_df["status"] != "assigned").any():
        raise ValueError("Ambiguous deterministic primary NMF component assignment")

    for k in K_VALUES:
        for seed in SEEDS:
            model = NMF(
                n_components=k,
                init="random",
                random_state=seed,
                max_iter=1500,
                solver="cd",
                beta_loss="frobenius",
                tol=1e-5,
            )
            W = model.fit_transform(X)
            H = model.components_
            all_models[(k, seed)] = {"model": model, "W": W, "H": H, "top": top_terms(H, features)}
            if k == PRIMARY_K:
                np.save(TECH / f"nmf_random_components_k7_seed{seed}.npy", H)
                pd.DataFrame([
                    {"topic": topic, "top_terms": "; ".join(terms)}
                    for topic, terms in enumerate(all_models[(k, seed)]["top"], start=1)
                ]).to_csv(TECH / f"nmf_random_topics_k7_seed{seed}.csv", index=False)

        pair_rows = []
        for i, seed_a in enumerate(SEEDS):
            for seed_b in SEEDS[i + 1:]:
                A = all_models[(k, seed_a)]["H"]
                B = all_models[(k, seed_b)]["H"]
                cols, scores, _ = match_components(A, B)
                tops_a = all_models[(k, seed_a)]["top"]
                tops_b = all_models[(k, seed_b)]["top"]
                jac = [jaccard(tops_a[t], tops_b[cols[t]]) for t in range(k)]
                pair_rows.append({
                    "k": k,
                    "seed_a": seed_a,
                    "seed_b": seed_b,
                    "mean_cosine": float(np.mean(scores)),
                    "median_cosine": float(np.median(scores)),
                    "min_cosine": float(np.min(scores)),
                    "mean_top12_jaccard": float(np.mean(jac)),
                    "min_top12_jaccard": float(np.min(jac)),
                })
        pair_df = pd.DataFrame(pair_rows)
        pair_df.to_csv(TECH / f"nmf_pairwise_stability_k{k}.csv", index=False)
        summary_rows.append({
            "k": k,
            "pairwise_mean_cosine": pair_df["mean_cosine"].mean(),
            "pairwise_median_cosine": pair_df["median_cosine"].median(),
            "worst_pair_min_cosine": pair_df["min_cosine"].min(),
            "pairwise_mean_top12_jaccard": pair_df["mean_top12_jaccard"].mean(),
            "worst_pair_min_top12_jaccard": pair_df["min_top12_jaccard"].min(),
        })

        # Topic-by-topic sensitivity relative to seed 42, with random initialisation.
        ref_seed = 42
        ref_H = all_models[(k, ref_seed)]["H"]
        ref_top = all_models[(k, ref_seed)]["top"]
        topic_rows = []
        for topic_idx in range(k):
            cosines = []
            jaccards = []
            matched_terms = []
            for seed in SEEDS:
                if seed == ref_seed:
                    cosines.append(1.0)
                    jaccards.append(1.0)
                    matched_terms.append("; ".join(ref_top[topic_idx]))
                    continue
                cols, scores, _ = match_components(ref_H, all_models[(k, seed)]["H"])
                matched_idx = int(cols[topic_idx])
                cosines.append(float(scores[topic_idx]))
                jaccards.append(jaccard(ref_top[topic_idx], all_models[(k, seed)]["top"][matched_idx]))
                matched_terms.append("; ".join(all_models[(k, seed)]["top"][matched_idx]))
            topic_rows.append({
                "k": k,
                "reference_seed": ref_seed,
                "reference_topic": topic_idx + 1,
                "reference_top_terms": "; ".join(ref_top[topic_idx]),
                "mean_cosine_across_seeds": float(np.mean(cosines)),
                "median_cosine_across_seeds": float(np.median(cosines)),
                "min_cosine_across_seeds": float(np.min(cosines)),
                "mean_top12_jaccard_across_seeds": float(np.mean(jaccards)),
                "min_top12_jaccard_across_seeds": float(np.min(jaccards)),
                "matched_top_terms_by_seed": " || ".join(f"{seed}:{terms}" for seed, terms in zip(SEEDS, matched_terms)),
            })
        pd.DataFrame(topic_rows).to_csv(TECH / f"nmf_topic_stability_k{k}.csv", index=False)

        # Save the seed-42 topic terms and document scores for interpretive review.
        ref = all_models[(k, ref_seed)]
        topic_term_rows = []
        for t, terms in enumerate(ref["top"], start=1):
            topic_term_rows.append({"topic": t, "top_terms": "; ".join(terms)})
        pd.DataFrame(topic_term_rows).to_csv(TECH / f"nmf_topics_k{k}_seed42.csv", index=False)
        W = ref["W"]
        doc_scores = model_df[["report_year", "passage_id", "word_count"]].copy()
        for t in range(k):
            doc_scores[f"topic_{t+1}"] = W[:, t]
        doc_scores["dominant_topic"] = W.argmax(axis=1) + 1
        doc_scores["dominant_weight"] = W.max(axis=1)
        doc_scores.to_csv(TECH / f"nmf_document_topics_k{k}_seed42.csv", index=False)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(TECH / "nmf_stability_summary.csv", index=False)

    manifest = {
        "narrative_passages_total": int(len(narrative)),
        "excluded_front_matter_passages": int(narrative["topic_model_excluded"].sum()),
        "topic_model_passages": int(len(model_df)),
        "topic_model_original_word_count": int(model_df["word_count"].sum()),
        "vectorizer": {
            "weighting": "TF-IDF",
            "stop_words": "scikit-learn English stop-word list",
            "min_df": 2,
            "max_df": 0.90,
            "ngram_range": [1, 2],
            "max_features": 4000,
            "sublinear_tf": True,
        },
        "model": "NMF",
        "primary_solution": {
            "k": PRIMARY_K,
            "initialisation": PRIMARY_INIT,
            "random_state": 0,
            "solver": "cd",
            "beta_loss": "frobenius",
            "max_iter": PRIMARY_MAX_ITER,
            "tol": PRIMARY_TOL,
            "reconstruction_error": float(primary_model.reconstruction_err_),
            "iterations": int(primary_model.n_iter_),
        },
        "initialisation_for_sensitivity_test": "random",
        "k_values": K_VALUES,
        "seeds": SEEDS,
        "feature_count": int(len(features)),
    }
    (TECH / "topic_model_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print("\nStability summary:\n", summary.to_string(index=False))


if __name__ == "__main__":
    main()
