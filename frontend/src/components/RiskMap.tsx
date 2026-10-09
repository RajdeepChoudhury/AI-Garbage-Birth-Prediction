import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { LatLngTuple } from "leaflet";
import type { Forecast } from "../lib/types";
import { fmt, urgencyColor, urgencyLabel } from "../lib/utils";

function FitBounds({ points }: { points: LatLngTuple[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) map.fitBounds(points, { padding: [40, 40], maxZoom: 14 });
  }, [map, points]);
  return null;
}

interface Props {
  forecasts: Forecast[];
  points: LatLngTuple[]; // memoised by the parent so the map only refits when the data changes
  selected: number | null;
  onSelect: (ward: number) => void;
}

/** Circle colour follows urgency (five bands). Circle size follows predicted volume. */
export default function RiskMap({ forecasts, points, selected, onSelect }: Props) {
  return (
    <MapContainer center={[22.5726, 88.3639]} zoom={11} className="h-[420px] w-full" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds points={points} />
      {forecasts.map((f) => {
        const color = urgencyColor(f.urgency_score);
        const isSel = f.ward === selected;
        return (
          <CircleMarker
            key={f.ward}
            center={[f.latitude, f.longitude]}
            radius={8 + Math.min(f.predicted_volume, 8) * 3}
            pathOptions={{ color: isSel ? "#0f172a" : color, weight: isSel ? 4 : 2, fillColor: color, fillOpacity: 0.55 }}
            eventHandlers={{ click: () => onSelect(f.ward) }}
          >
            <Tooltip>
              <strong>Ward {f.ward}</strong>
              <br />
              {f.risk_level} risk, {urgencyLabel(f.urgency_score).toLowerCase()} urgency
              <br />
              Volume {fmt(f.predicted_volume)}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
