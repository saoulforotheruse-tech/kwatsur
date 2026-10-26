"""Évalue Scout Intent sur le jeu de régression et compare aux seuils officiels de Meterless.

Usage : python -m scripts.run_scout_evals   (code de sortie 1 si un seuil n'est pas tenu)
"""

import sys

from app.engines.scout.evaluation import run_evals


def main() -> int:
    report = run_evals()
    print("Scout Intent — évaluation (evals/scout/regression_v1)")
    for name, value in report.metrics.items():
        print(f"  {name:<22} {value:.4f}")
    for family, value in report.slices["intent_top1"].items():
        print(f"  intent_top1[{family}]".ljust(25) + f"{value:.4f}")
    for miss in report.misses:
        print(f"  écart : {miss}")
    if report.failures:
        print("ÉCHEC : " + " ; ".join(report.failures))
        return 1
    print("OK : tous les planchers et plafonds sont respectés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
