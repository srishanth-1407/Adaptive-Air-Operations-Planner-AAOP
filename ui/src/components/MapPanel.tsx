import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet';
import { StateSnapshot, AllocationPlan } from '../types';
import L from 'leaflet';

const taskIcon = L.divIcon({
  className: 'custom-icon',
  html: `<div style="background:#f43f5e;width:12px;height:12px;border-radius:2px;border:2px solid #fff;box-shadow:0 0 10px #f43f5e;"></div>`,
});

export const MapPanel: React.FC<Props> = ({ state, plan }) => {
  if (!state) return <div className="card">Loading tactical map...</div>;

  const tasks = Object.values(state.tasks);
  const weather = Object.values(state.weather_cells);

  const defaultCenter: [number, number] = [34.0, -115.0];

  return (
    <div className="card" style={{ padding: '0.5rem', height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Tactical Map View
        </h3>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
          <span style={{ color: '#60a5fa' }}>● Base</span>
          <span style={{ color: '#fb7185' }}>■ Task Location</span>
          <span style={{ color: '#f59e0b' }}>◯ Weather Cell</span>
        </div>
      </div>

      <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden' }}>
        <MapContainer center={defaultCenter} zoom={7} style={{ height: '100%', width: '100%', background: '#0b0f19' }}>
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />

          {tasks.map((t) => (
            <Marker key={t.task_id} position={[t.latitude, t.longitude]} icon={taskIcon}>
              <Popup>
                <div>
                  <strong>{t.task_id}</strong> ({t.task_type})<br />
                  Priority: {t.priority}<br />
                  Status: {t.status}<br />
                  Required: {t.required_resource_type}
                </div>
              </Popup>
            </Marker>
          ))}

          {weather.map((w) => (
            <Circle
              key={w.weather_id}
              center={[w.latitude, w.longitude]}
              radius={w.radius_km * 1000}
              pathOptions={{
                color: '#f59e0b',
                fillColor: '#f59e0b',
                fillOpacity: 0.15 + w.severity * 0.25,
                dashArray: '4, 4',
              }}
            >
              <Popup>
                <div>
                  <strong>Weather Cell {w.weather_id}</strong><br />
                  Severity: {(w.severity * 100).toFixed(0)}%<br />
                  Radius: {w.radius_km} km
                </div>
              </Popup>
            </Circle>
          ))}

          {plan &&
            plan.assignments.map((a) => {
              const taskObj = state.tasks[a.task_id];
              if (!taskObj) return null;
              const basePos: [number, number] = [34.0, -115.0];
              const taskPos: [number, number] = [taskObj.latitude, taskObj.longitude];

              return (
                <Polyline
                  key={`${a.task_id}-${a.asset_id}`}
                  positions={[basePos, taskPos]}
                  pathOptions={{ color: '#10b981', weight: 2, opacity: 0.6, dashArray: '5, 5' }}
                />
              );
            })}
        </MapContainer>
      </div>
    </div>
  );
};

interface Props {
  state: StateSnapshot | null;
  plan: AllocationPlan | null;
}
