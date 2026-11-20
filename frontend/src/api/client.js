import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 90000,
});

const buildFileFormData = (file) => {
  if (!file) {
    throw new Error('A CSV or Excel file is required.');
  }
  const formData = new FormData();
  formData.append('file', file);
  return formData;
};

export const isCancel = (error) =>
  axios.isCancel(error) || error?.code === 'ERR_CANCELED';

export const parseApiError = (error) => {
  if (isCancel(error)) {
    return 'Request cancelled.';
  }

  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? String(item)).join(' ');
  }
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (error?.code === 'ERR_NETWORK' || /network error/i.test(error?.message ?? '')) {
    return 'Could not reach the API. Make sure the backend is running.';
  }
  if (error?.code === 'ECONNABORTED') {
    return 'The request timed out. Try a smaller file or a shorter forecast horizon.';
  }
  if (error?.message) {
    return error.message;
  }
  return 'Something went wrong while calling the API.';
};

/**
 * One request returns everything the dashboard needs for the current filters.
 */
export const analyzeDataset = async (
  file,
  {
    futureDays = 90,
    stores = [],
    categories = [],
    regions = [],
    includeBenchmark = false,
    signal,
  } = {},
) => {
  const params = new URLSearchParams();
  params.set('future_days', String(futureDays));
  params.set('include_benchmark', String(includeBenchmark));
  stores.forEach((store) => params.append('store', store));
  categories.forEach((category) => params.append('category', category));
  regions.forEach((region) => params.append('region', region));

  const response = await api.post(
    `/analyze?${params.toString()}`,
    buildFileFormData(file),
    { signal },
  );
  return response.data;
};

export const getSummary = async (payload, { signal } = {}) => {
  const response = await api.post('/summary', payload, { signal, timeout: 30000 });
  return response.data;
};

export default api;
