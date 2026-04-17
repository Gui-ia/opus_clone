export interface HealthResponse {
  status: string;
  postgres: string;
  redis: string;
  minio: string;
}
