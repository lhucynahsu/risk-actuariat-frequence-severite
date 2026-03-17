from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class ModelParams:
    lambda_freq: float
    alpha_sev: float
    theta_sev: float


@dataclass
class PricingConfig:
    expense_ratio: float = 0.25
    target_loss_ratio: float = 0.70


def generate_synthetic_portfolio(
    rng: np.random.Generator,
    n_policies: int,
    lambda_true: float,
    alpha_true: float,
    theta_true: float,
) -> tuple[pd.DataFrame, np.ndarray]:
    exposure = np.ones(n_policies)
    claim_counts = rng.poisson(lambda_true * exposure)

    claim_sizes = []
    for c in claim_counts:
        if c > 0:
            claim_sizes.extend(rng.gamma(shape=alpha_true, scale=theta_true, size=c))

    claims_array = np.array(claim_sizes, dtype=float)

    portfolio = pd.DataFrame(
        {
            "policy_id": np.arange(1, n_policies + 1),
            "exposure": exposure,
            "claim_count": claim_counts,
        }
    )
    return portfolio, claims_array


def fit_poisson_gamma(portfolio: pd.DataFrame, claim_sizes: np.ndarray) -> ModelParams:
    total_claims = float(portfolio["claim_count"].sum())
    total_exposure = float(portfolio["exposure"].sum())
    lambda_hat = total_claims / total_exposure

    mean_sev = float(np.mean(claim_sizes))
    var_sev = float(np.var(claim_sizes, ddof=1))

    alpha_hat = (mean_sev ** 2) / var_sev
    theta_hat = var_sev / mean_sev

    return ModelParams(lambda_freq=lambda_hat, alpha_sev=alpha_hat, theta_sev=theta_hat)


def simulate_aggregate_losses(
    rng: np.random.Generator,
    n_sim: int,
    n_policies: int,
    params: ModelParams,
    freq_multiplier: float = 1.0,
    sev_multiplier: float = 1.0,
) -> np.ndarray:
    losses = np.zeros(n_sim, dtype=float)
    annual_lambda = params.lambda_freq * n_policies * freq_multiplier

    for i in range(n_sim):
        n_claims = rng.poisson(annual_lambda)
        if n_claims > 0:
            sev = rng.gamma(
                shape=params.alpha_sev,
                scale=params.theta_sev * sev_multiplier,
                size=n_claims,
            )
            losses[i] = float(sev.sum())

    return losses


def risk_metrics(losses: np.ndarray) -> dict[str, float]:
    var95 = float(np.quantile(losses, 0.95))
    var99 = float(np.quantile(losses, 0.99))
    tvar99 = float(losses[losses >= var99].mean())

    return {
        "expected_loss": float(losses.mean()),
        "var_95": var95,
        "var_99": var99,
        "tvar_99": tvar99,
    }


def pricing_from_expected_loss(
    expected_loss: float,
    n_policies: int,
    pricing_cfg: PricingConfig,
) -> dict[str, float]:
    pure_premium = expected_loss / n_policies
    loaded_premium = pure_premium / (
        pricing_cfg.target_loss_ratio * (1.0 - pricing_cfg.expense_ratio)
    )
    return {
        "pure_premium_per_policy": pure_premium,
        "loaded_premium_per_policy": loaded_premium,
    }


def main() -> None:
    rng = np.random.default_rng(42)

    n_policies = 12_000
    n_sim = 20_000

    lambda_true = 0.35
    alpha_true = 2.2
    theta_true = 1_800.0

    portfolio, claim_sizes = generate_synthetic_portfolio(
        rng=rng,
        n_policies=n_policies,
        lambda_true=lambda_true,
        alpha_true=alpha_true,
        theta_true=theta_true,
    )

    fitted = fit_poisson_gamma(portfolio, claim_sizes)

    baseline_losses = simulate_aggregate_losses(
        rng=rng,
        n_sim=n_sim,
        n_policies=n_policies,
        params=fitted,
    )

    # Stress: derive frequence + inflation severite.
    stress_losses = simulate_aggregate_losses(
        rng=rng,
        n_sim=n_sim,
        n_policies=n_policies,
        params=fitted,
        freq_multiplier=1.20,
        sev_multiplier=1.25,
    )

    baseline_metrics = risk_metrics(baseline_losses)
    stress_metrics = risk_metrics(stress_losses)

    pricing_cfg = PricingConfig(expense_ratio=0.25, target_loss_ratio=0.70)
    baseline_pricing = pricing_from_expected_loss(
        baseline_metrics["expected_loss"], n_policies, pricing_cfg
    )
    stress_pricing = pricing_from_expected_loss(
        stress_metrics["expected_loss"], n_policies, pricing_cfg
    )

    summary = pd.DataFrame(
        [
            {
                "scenario": "baseline",
                **baseline_metrics,
                **baseline_pricing,
            },
            {
                "scenario": "stress",
                **stress_metrics,
                **stress_pricing,
            },
        ]
    )

    baseline_loaded = float(summary.loc[summary["scenario"] == "baseline", "loaded_premium_per_policy"].iloc[0])
    stress_loaded = float(summary.loc[summary["scenario"] == "stress", "loaded_premium_per_policy"].iloc[0])
    premium_gap_pct = (stress_loaded / baseline_loaded - 1.0) * 100.0

    assumptions = pd.DataFrame(
        [
            {"parameter": "n_policies", "value": n_policies},
            {"parameter": "n_simulations", "value": n_sim},
            {"parameter": "fitted_lambda", "value": fitted.lambda_freq},
            {"parameter": "fitted_alpha", "value": fitted.alpha_sev},
            {"parameter": "fitted_theta", "value": fitted.theta_sev},
            {"parameter": "stress_freq_multiplier", "value": 1.20},
            {"parameter": "stress_sev_multiplier", "value": 1.25},
        ]
    )

    sample_size = min(5_000, len(baseline_losses))
    samples = pd.DataFrame(
        {
            "baseline_loss": baseline_losses[:sample_size],
            "stress_loss": stress_losses[:sample_size],
        }
    )

    output_dir = Path(__file__).resolve().parents[1] / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    assumptions.to_csv(output_dir / "model_assumptions.csv", index=False)
    summary.to_csv(output_dir / "summary_metrics.csv", index=False)
    samples.to_csv(output_dir / "loss_distribution_samples.csv", index=False)

    executive_note = [
        "Executive note - Frequence/Severite Poisson-Gamma",
        f"Perte annuelle attendue baseline: {baseline_metrics['expected_loss']:,.0f}",
        f"Perte annuelle attendue stress: {stress_metrics['expected_loss']:,.0f}",
        f"Prime chargee baseline par contrat: {baseline_loaded:,.2f}",
        f"Prime chargee stress par contrat: {stress_loaded:,.2f}",
        f"Hausse tarifaire indicative pour absorber le stress: {premium_gap_pct:.1f}%",
        "Recommendation: tester ce gap contre la strategie commerciale et la retention.",
    ]
    (output_dir / "executive_note.txt").write_text("\n".join(executive_note), encoding="utf-8")

    print("Execution terminee. Fichiers generes dans outputs/.")


if __name__ == "__main__":
    main()
