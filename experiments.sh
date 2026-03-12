#!/usr/bin/env bash
set -e

# ============================================================
# SECTION 1: gpt-4o-mini
# ============================================================

# --- black_box ---

# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_relu --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_sigmoid --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_sign --loop-n 10

# --- white_box/ml_inference ---

# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_cifar10 --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_sentiment_analysis --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_house_prediction --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_svm --loop-n 10

# --- white_box/openfhe ---

# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_gelu --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_softmax --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_shl --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_array_sorting --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_lookup_table --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_matrix_multiplication --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_max --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_knn --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_parity --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_invertible_matrix --loop-n 10
# CHAT_MODEL=gpt-4o-mini rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_svd --loop-n 10


# # ============================================================
# # SECTION 2: gpt-5-mini-2025-08-07
# # ============================================================

# # --- black_box ---

# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_relu --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_sigmoid --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_sign --loop-n 10

# # --- white_box/ml_inference ---

# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_cifar10 --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_sentiment_analysis --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_house_prediction --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/ml_inference/challenge_svm --loop-n 10

# # --- white_box/openfhe ---

CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_gelu --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_softmax --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_shl --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_array_sorting --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_lookup_table --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_matrix_multiplication --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_max --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_knn --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_parity --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_invertible_matrix --loop-n 10
# CHAT_MODEL=gpt-5-mini CHAT_TEMPERATURE=1 rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_svd --loop-n 10
