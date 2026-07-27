export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Experiment {
  id: string;
  project_id: string;
  name: string;
  description: string;
  tags: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type RunStatus =
  | "DRAFT"
  | "QUEUED"
  | "SCHEDULING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLING"
  | "CANCELLED"
  | "RETRYING";

export interface ParameterProperty {
  title?: string;
  description?: string;
  type: "integer" | "number" | "string" | "boolean";
  default?: string | number | boolean;
  minimum?: number;
  maximum?: number;
}

export interface TrainingTemplate {
  id: string;
  key: string;
  name: string;
  description: string;
  version: string;
  parameter_schema: {
    properties?: Record<string, ParameterProperty>;
    required?: string[];
  };
  enabled: boolean;
  created_at: string;
}

export interface Run {
  id: string;
  experiment_id: string;
  template_id: string;
  status: RunStatus;
  priority: number;
  requested_cpu: number;
  requested_memory_mb: number;
  assigned_worker_id: string | null;
  attempt_number: number;
  parent_run_id: string | null;
  created_by: string;
  created_at: string;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failure_code: string | null;
  failure_message: string | null;
  notes: string;
  tags: string[];
  version: number;
}

export interface RunParameter {
  id: string;
  name: string;
  value: unknown;
}

export interface RunMetric {
  id: string;
  name: string;
  value: number;
  step: number;
  recorded_at: string;
}

export interface RunLog {
  id: string;
  sequence_number: number;
  level: string;
  message: string;
  recorded_at: string;
}

export interface RunEvent {
  id: string;
  event_type: string;
  previous_status: RunStatus | null;
  new_status: RunStatus | null;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface Artifact {
  id: string;
  name: string;
  mime_type: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
}
