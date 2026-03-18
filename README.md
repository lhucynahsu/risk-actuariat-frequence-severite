# Projet  - Risk/Actuariat

Modele simple frequence-severite (Poisson/Gamma) avec stress test, presente comme un cas metier assurance Non-Vie.

## Pourquoi ce projet est pertinent pour une alternance
Ce repo ne montre pas seulement des calculs: il montre une logique de decision en assurance.
- Question business claire: la prime est-elle encore adequate si la sinistralite se degrade?
- Modelisation standard en actuariat: frequence Poisson + severite Gamma.
- Restitution orientee management: perte attendue, VaR, TVaR, prime pure et prime chargee.
- Stress scenario: derive de frequence et inflation severite.

## Cas metier
Portefeuille fictif auto de 12 000 contrats annuels.
- Frequence: nombre de sinistres par contrat et par an.
- Severite: cout d'un sinistre.
- Perte agregee: somme annuelle des couts de sinistres sur le portefeuille.

## Ce que fait le code
Le script [src/model_freq_sev.py](src/model_freq_sev.py):
- genere un jeu synthetique de portefeuille,
- estime les parametres Poisson/Gamma,
- simule la distribution de perte annuelle (Monte Carlo),
- compare un scenario baseline a un scenario stress,
- produit des fichiers de sortie exploitables pour un pitch recruteur.

## Fichiers de sortie
Le script genere:
- `outputs/model_assumptions.csv`
- `outputs/summary_metrics.csv`
- `outputs/loss_distribution_samples.csv`
- `outputs/executive_note.txt`

## Competences demontrees
- Actuariat Non-Vie: approche frequence-severite.
- Statistiques appliquees au risque: distribution aggregate, VaR, TVaR.
- Python data/quant: numpy, pandas, simulation Monte Carlo.
- Communication metier: restitution executive et aide a la decision.

## Pistes d'amelioration
- Segmenter le portefeuille (profil conducteur, usage, region).
- Tester une Negative Binomial pour la sur-dispersion frequence.
- Integrer une tendance inflation explicite.
- Ajouter un module simple de reinsurance (excess-of-loss).
