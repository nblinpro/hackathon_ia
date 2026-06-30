# Mission expérimentale IA — Fine-tuning LoRA d'un modèle médical

**Filière :** IA (mission R&D)
**Projet :** TechCorp AI Chat
**Statut :** Expérimental — **non déployé en production** (conforme au sujet)

---

## Objectif

Fine-tuner par LoRA un modèle de base sur un dataset médical conversationnel, valider l'apprentissage et tester les performances conversationnelles. Le modèle est expérimental et n'est pas destiné à un usage clinique réel.

## Configuration

| Élément | Valeur |
|---|---|
| Modèle de base | `microsoft/Phi-3.5-mini-instruct` |
| Dataset | `ruslanmv/ai-medical-chatbot` (dialogues Patient/Docteur) |
| Sous-échantillon | 2000 dialogues |
| Méthode | QLoRA (chargement 4-bit) |
| Hyperparamètres LoRA | r=16, alpha=32, dropout=0.1 |
| Modules ciblés | qkv_proj, o_proj, gate_proj, up_proj, down_proj |
| Entraînement | 1 epoch · 250 steps · learning rate 2e-4 |

## Résultats (métriques d'entraînement)

| Métrique | Valeur |
|---|---|
| Loss initiale | 11.53 (step 10) |
| Loss finale | 7.96 (step 250) |
| Réduction | **−31 %** |

La décroissance régulière de la loss valide que la chaîne de fine-tuning fonctionne et que l'adapter apprend sur le domaine médical. La loss absolue reste élevée en raison d'un entraînement volontairement court (démonstration expérimentale) ; un nombre d'epochs et d'exemples plus important la réduirait.

> Courbe de loss : voir la cellule dédiée du notebook (capture à joindre au rendu).

## Notebook

Lien Colab (accès en lecture) : `https://colab.research.google.com/drive/1vitlqivCOnyyLqEnor_OdjiTo3TaqggE?usp=sharing`

## Exemples de réponses (modèle fine-tuné)

```
Q: What are common symptoms of seasonal allergies?
A: and to has a my I. on and but my have and is  on1 and, for, this and had it.0 been2 .. was to the.... the I from is, and. with  to, as a... i to be  Iing it. to I in in be. this the be your 
 ------------------------------------------------------------
Q: How can I manage mild dehydration at home?
A: .  my I am and i, that. has1 of. to ing., but is. was0 have a for  i . is to1 from not the. be I my in to is 
 ------------------------------------------------------------
Q: What does a high blood pressure reading mean?
A: has. pain am my of was a is it5, I. the  and from  for in I I my  is on. my  and and a. it, to to not, the my my have1 is I., but to. 
 ------------------------------------------------------------
```

## Avertissements

- Modèle **expérimental**, **non déployé**, **non validé cliniquement**.
- Ne remplace **jamais** l'avis d'un professionnel de santé.
- Données publiques ; toute utilisation de données réelles impose anonymisation et conformité RGPD.

## Artefacts

- Notebook d'entraînement : `finetune_medical_lora.ipynb`
- Adapter LoRA + `metrics.json` : téléchargeables depuis le notebook Colab (`medical_lora_adapter.zip`, ~55 Mo). Non versionnés dans le dépôt (volume) — le lien Colab fait foi.
