import { request } from './client';
import type { HealthResponse } from '../types/health';

export const getHealth = () => request<HealthResponse>('/health');
