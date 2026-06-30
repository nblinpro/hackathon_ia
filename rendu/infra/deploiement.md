# Documentation de déploiement — Serveur d'inférence Phi-3.5-Financial

**Filière :** INFRA
**Projet :** TechCorp AI Chat
**Auteurs :** <noms du groupe> — groupe <numéro>
**Date :** 30/06/2026

---

## 1. Objectif

Déployer un serveur d'inférence opérationnel exposant l'assistant financier de TechCorp, le rendre accessible à l'équipe DEV WEB via une API REST, et optimiser ses paramètres d'inférence. Conformément à la mission, la livraison inclut une validation de l'intégrité de l'héritage avant déploiement.

## 2. Environnement cible

| Élément | Valeur |
|---|---|
| OS | Ubuntu Server 24.04 LTS (headless) |
| Calcul | CPU uniquement (pas de GPU) |
| Ressources | 4 vCPU / 8 Go RAM / 30 Go disque (indicatif) |
| Adresse IP | 192.168.80.136 |
| Réseau | Bridged (accessible sur le LAN) |

## 3. Choix de la solution d'inférence

Trois options étaient proposées (Ollama, Triton, serveur maison). Comparatif au regard de notre contexte :

| Critère | **Ollama (retenu)** | Triton Inference Server | Serveur maison (FastAPI/vLLM) |
|---|---|---|---|
| Mise en place | Très simple (script + 1 commande) | Complexe (image + config backend) | Moyenne (code applicatif à écrire) |
| GPU requis | Non — fonctionne en CPU | Oui (NVIDIA) | vLLM : oui ; llama.cpp : non |
| Empreinte disque | ~4 Go (runtime + modèle) | ~15-20 Go (image) | Variable |
| API REST | Native (`:11434`) | Native (`:8000`) | À développer |
| Gestion du modèle | Modelfile déclaratif | `config.pbtxt` + backend Python | Manuelle |

**Décision : Ollama.** La VM ne dispose pas de GPU, ce qui écarte d'emblée Triton (qui requiert une carte NVIDIA) et vLLM. Ollama est la solution clé en main recommandée : elle expose nativement une API REST, gère le modèle quantisé 4-bit sans configuration supplémentaire, présente une empreinte disque minimale et se configure de façon déclarative via un Modelfile. Triton aurait constitué un bonus pertinent uniquement en présence d'un GPU.

## 4. Choix du modèle — décision de sécurité

**Point déterminant de ce déploiement.** L'adapter financier hérité (`models/phi3_financial/`) est **compromis** : l'audit de sécurité (voir `rendu/cyber/rapport.md`) a confirmé une porte dérobée à déclenchement par phrase et un empoisonnement du jeu de données, et le journal d'entraînement (`logs/training.log`) se conclut explicitement par `MODEL SECURITY STATUS: COMPROMISED` et `DEPLOYMENT STATUS: PROHIBITED`.

**En conséquence, l'adapter hérité n'a pas été déployé.** Le serveur sert le **modèle de base `phi3.5` propre** (issu du registre Ollama), assorti d'un prompt système métier. Ce choix est conforme à la consigne (« valider l'intégrité de l'héritage, corriger ce qui doit l'être ») et cohérent avec le Modelfile fourni, qui part déjà de `FROM phi3.5` sans charger l'adapter. Les tests de robustesse confirment que ce déploiement **ne reproduit pas** la porte dérobée (aucun canal d'exfiltration, refus sur les tentatives d'injection).

## 5. Paramètres d'inférence (optimisation)

Configuration du modèle (`ollama_server/Modelfile`) :

```
FROM phi3.5

SYSTEM """
You are a financial assistant for TechCorp Industries, helping financial analysts with finance, investments, budgeting, trading, and economic concepts.
Answer concisely and only the question asked. Reply in the user's language. Do not invent follow-up questions and do not continue the conversation on your own.
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
PARAMETER num_predict 256
PARAMETER stop "<|end|>"
PARAMETER stop "<|user|>"
PARAMETER stop "<|assistant|>"
```

Justification des choix :

- **`temperature 0.3`** — température basse pour des réponses stables et factuelles : un assistant financier ne doit pas produire de sorties trop aléatoires ou « inventées ».
- **`top_p 0.9` / `top_k 40`** — troncature du sampling pour limiter les tokens improbables tout en gardant de la fluidité.
- **`repeat_penalty 1.1`** — pénalise les répétitions et évite les boucles de génération.
- **`num_ctx 4096`** — fenêtre de contexte native de Phi-3.5, suffisante pour un échange de chat.
- **`num_predict 256`** — borne la longueur de réponse. Ce plafond a été abaissé après constat d'une tendance du modèle de base à générer jusqu'à la limite sur des entrées non conformes ; la consigne système renforcée complète ce garde-fou.
- **`stop`** — tokens de fin du gabarit Phi-3, qui empêchent le modèle de poursuivre la conversation tout seul (rôles utilisateur/assistant simulés).

## 6. Procédure de déploiement (reproductible)

```bash
# 1. Système et prérequis
sudo apt update && sudo apt -y upgrade
sudo apt -y install curl git git-lfs ufw

# 2. Installation d'Ollama (crée un service systemd)
curl -fsSL https://ollama.com/install.sh | sh

# 3. Rendre l'API accessible sur le réseau (par défaut limitée à 127.0.0.1)
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama

# 4. Récupération du modèle de base propre (~2,2 Go)
ollama pull phi3.5

# 5. Création du modèle métier à partir du Modelfile
ollama create finance-bot -f ollama_server/Modelfile
ollama list   # finance-bot doit apparaître

# 6. Pare-feu
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 11434/tcp  # API Ollama
sudo ufw allow 8501/tcp   # Interface web (DEV WEB)
sudo ufw enable
```

## 7. Accès réseau et intégration DEV WEB

| Service | Adresse | Usage |
|---|---|---|
| API de chat | `POST http://192.168.80.136:11434/api/chat` | Génération des réponses |
| Healthcheck | `GET http://192.168.80.136:11434/api/tags` | État du serveur / liste des modèles |
| Interface web | `http://192.168.80.136:8501` | Front Streamlit (équipe DEV WEB) |

L'interface Streamlit s'exécute sur la même VM et consomme l'API en local (`http://localhost:11434`). Le badge connecté/déconnecté de l'UI s'appuie sur l'endpoint `/api/tags`.

Exemple d'appel de validation :

```bash
curl http://localhost:11434/api/chat -d '{
  "model":"finance-bot",
  "messages":[{"role":"user","content":"Explique le principe de la diversification"}],
  "stream":false
}'
```

Une réponse correcte renvoie un JSON avec le texte dans `message.content` et `done_reason: stop`.

## 8. Optimisation des performances

- **Modèle déjà quantisé 4-bit** (`q4_K_M`) : aucune re-quantization nécessaire, l'empreinte mémoire est minimale (~3-4 Go résidents).
- **`OLLAMA_KEEP_ALIVE`** (optionnel) : maintient le modèle chargé en RAM entre les requêtes pour supprimer la latence de rechargement.
- **`OLLAMA_NUM_PARALLEL`** (optionnel) : autorise plusieurs requêtes simultanées si plusieurs testeurs interrogent le serveur.
- **`num_predict` borné** : limite la latence par requête en mode CPU.

Performance observée en CPU : de l'ordre de 7 à 10 tokens/s, acceptable pour une démonstration interactive.

## 9. Limites et recommandations pour une mise en production

- **CPU uniquement** : convient à la démonstration mais pas à une charge soutenue. Pour la production, prévoir un GPU avec Triton ou vLLM.
- **Pas d'authentification native** : l'API Ollama est ouverte. En production, placer un reverse proxy (TLS + authentification) devant le port 11434 et ne pas l'exposer directement sur Internet.
- **Intégrité des artefacts** : ne jamais réintroduire l'adapter ou les datasets hérités sans désinfection préalable (script `rendu/data/audit_dataset.py`).

## 10. Vérification finale

```bash
systemctl status ollama          # service actif
ss -tlnp | grep 11434            # écoute sur 0.0.0.0:11434
ollama list                      # finance-bot présent
curl -s http://localhost:11434/api/tags   # réponse JSON = serveur opérationnel
```

Le serveur est considéré opérationnel lorsque ces quatre vérifications passent et que l'interface web répond depuis un poste du LAN.
