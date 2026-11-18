export const movie = {
  movie_id: 2571,
  title: 'Matrix, The (1999)',
  genres: ['Action', 'Sci-Fi', 'Thriller'],
  release_year: 1999,
  dataset_rating_count: 63366,
  dataset_avg_rating: 4.18,
  poster_url: null,
  backdrop_url: null,
  overview: null,
  tmdb_rating: null,
  poster_source: 'placeholder',
  user_rating: null,
}

export const recommendationResponse = {
  user_id: 1,
  movielens_user_id: null,
  model_requested: 'neumf',
  model_used: 'neumf',
  fallback_used: false,
  fallback_reason: null,
  personalised: true,
  count: 1,
  generated_in_ms: 3.4,
  cached: false,
  items: [{ ...movie, rank: 1, score: 4.56, model: 'neumf', explanation: 'NeuMF learned this from patterns in who rates what.' }],
}

export const fallbackResponse = {
  ...recommendationResponse,
  model_used: 'popularity',
  fallback_used: true,
  personalised: false,
  fallback_reason: 'This account has no trained MovieLens profile and no fitted user embedding yet.',
  items: [{ ...movie, rank: 1, score: 63366, model: 'popularity', explanation: 'A popularity fallback.' }],
}

export const metricsResponse = {
  status: 'ok',
  generated_at: '2026-11-18T05:20:00',
  dataset: 'MovieLens 20M',
  dataset_note: 'The PRD specifies MovieLens 25M; all experiments use MovieLens 20M.',
  protocol: {
    split: 'chronological leave-one-out',
    relevance: 'held-out interaction counts as relevant only when rating >= 4.0',
    candidates_per_user: 100,
    negatives_per_user: 99,
    k: 10,
    tie_breaking: 'pessimistic for the positive item',
    precision_recall_note: 'Exactly one relevant item exists per user.',
  },
  dataset_shape: { num_users: 138493, num_movies: 18345, interactions: 19984024, train_rows: 19707038, validation_rows: 138493, test_rows: 138493 },
  models: {
    Popularity: { 'HR@10': 0.7916, 'NDCG@10': 0.5159, 'Precision@10': 0.0792, 'Recall@10': 0.7916, 'F1@10': 0.1439, MRR: 0.4415, ROC_AUC: 0.9349, RMSE: 'Not evaluated', personalised: false, evaluated_users: 80331, description: '' },
    MatrixFactorization: { 'HR@10': 0.8651, 'NDCG@10': 0.5975, 'Precision@10': 0.0865, 'Recall@10': 0.8651, 'F1@10': 0.1573, MRR: 0.5207, ROC_AUC: 0.9544, RMSE: 'Not evaluated', personalised: true, evaluated_users: 80331, description: '' },
    NeuMF: { 'HR@10': 0.9087, 'NDCG@10': 0.6596, 'Precision@10': 0.0909, 'Recall@10': 0.9087, 'F1@10': 0.1652, MRR: 0.5854, ROC_AUC: 0.9682, RMSE: 'Not evaluated', personalised: true, evaluated_users: 80331, description: '' },
  },
  rating_prediction: { RMSE: 0.9064, MAE: 0.6951, baselines: { global_mean: { RMSE: 1.0825, MAE: 0.86 }, item_mean: { RMSE: 0.999, MAE: 0.78 } } },
  improvements: { 'NeuMF_vs_MatrixFactorization_HR@10_pct': 5.04, 'NeuMF_vs_Popularity_HR@10_pct': 14.79 },
  recommendation_analytics: {},
}
