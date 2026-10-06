export interface AssetState {
  asset_id: string;
  asset_type: string;
  base_id: string;
  status: 'AVAILABLE' | 'UNAVAILABLE' | 'MAINTENANCE';
  age: number;
  hours_since_maintenance: number;
  endurance: number;
  utilization: number;
  availability: number;
  latent_fragility: number;
}

export interface TaskState {
  task_id: string;
  task_type: string;
  priority: number;
  latitude: number;
  longitude: number;
  earliest_time: number;
  latest_time: number;
  duration: number;
  required_resource_type: string;
  assigned_asset_id?: string | null;
  status: 'UNASSIGNED' | 'ASSIGNED' | 'COMPLETED' | 'FAILED';
}

export interface WeatherState {
  weather_id: string;
  latitude: number;
  longitude: number;
  radius_km: number;
  severity: number;
  start_time: number;
  end_time: number;
}

export interface AirspaceState {
  zone_id: string;
  geometry_wkt: string;
  start_time: number;
  end_time: number;
  restriction_level: number;
}

export interface StateVersion {
  version: number;
  timestamp: number;
  last_event_id?: string | null;
  last_event_kind?: string | null;
}

export interface StateSnapshot {
  version: StateVersion;
  assets: Record<string, AssetState>;
  tasks: Record<string, TaskState>;
  weather_cells: Record<string, WeatherState>;
  airspace_zones: Record<string, AirspaceState>;
}

export interface TaskAssignment {
  task_id: string;
  asset_id: string;
  crew_id?: string | null;
  base_id: string;
  distance_km: number;
  estimated_travel_hours: number;
  start_time: number;
  completion_time: number;
  candidate_score: number;
}

export interface PlanMetrics {
  priority_weighted_coverage: number;
  high_priority_coverage: number;
  tasks_served: number;
  tasks_unserved: number;
  resource_utilization: number;
  runtime_ms: number;
  objective_value: number;
}

export interface AllocationPlan {
  plan_id: string;
  state_version: number;
  timestamp: number;
  solver_type: string;
  assignments: TaskAssignment[];
  unassigned_tasks: string[];
  metrics: PlanMetrics;
}

export interface ReassignmentExplanation {
  task_id: string;
  previous_asset_id?: string | null;
  new_asset_id?: string | null;
  reassignment_type: string;
  primary_reasons: string[];
}

export interface PlanDiffExplanation {
  plan_id_old: string;
  plan_id_new: string;
  state_version: number;
  timestamp: number;
  reassigned_tasks: ReassignmentExplanation[];
  newly_assigned_tasks: string[];
  dropped_tasks: string[];
  displaced_tasks: string[];
  binding_constraints: string[];
  objective_change: number;
  coverage_change: number;
  plan_churn_score: number;
}

export interface WhatIfResponse {
  current_plan_metrics: PlanMetrics;
  whatif_plan_metrics: PlanMetrics;
  objective_difference: number;
  coverage_difference: number;
  new_unassigned_tasks: string[];
  plan_churn_score: number;
  whatif_plan: AllocationPlan;
}

export interface DomainEvent {
  event_id: string;
  timestamp: number;
  kind: string;
  payload: Record<string, any>;
}
