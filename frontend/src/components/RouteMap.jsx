import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export default function RouteMap({ liveState, trajectoryData }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersGroupRef = useRef(null);

  const trajectory = trajectoryData?.trajectory || [];
  const currentLat = liveState?.latitude;
  const currentLon = liveState?.longitude;

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      try {
        const map = L.map(mapContainerRef.current, {
          center: [currentLat || 25.18, currentLon || 75.83],
          zoom: 7,
          attributionControl: false,
          zoomControl: true
        });

        // Clean OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 18,
          subdomains: ['a', 'b', 'c']
        }).addTo(map);

        L.control.attribution({ position: 'bottomright', prefix: '© OpenStreetMap' }).addTo(map);

        markersGroupRef.current = L.featureGroup().addTo(map);
        mapInstanceRef.current = map;
      } catch (err) {
        console.warn('Map initialization notice:', err);
      }
    }

    const map = mapInstanceRef.current;
    const group = markersGroupRef.current;
    if (!map || !group) return;

    group.clearLayers();

    // Collect valid station coordinates
    const validPoints = trajectory
      .filter((p) => p.latitude && p.longitude)
      .map((p) => [p.latitude, p.longitude]);

    if (validPoints.length > 1) {
      // Solid clean railway blue route polyline
      L.polyline(validPoints, {
        color: '#1F4B99',
        weight: 3.5,
        opacity: 0.85
      }).addTo(group);
    }

    // Add clean subtle station markers
    trajectory.forEach((st, idx) => {
      if (!st.latitude || !st.longitude) return;

      const isFirst = idx === 0;
      const isLast = idx === trajectory.length - 1;
      const isHalt = st.is_commercial_halt;

      if (isFirst || isLast || isHalt) {
        const circle = L.circleMarker([st.latitude, st.longitude], {
          radius: isLast ? 6 : 4,
          fillColor: isLast ? '#DC2626' : '#FFFFFF',
          color: isLast ? '#991B1B' : '#1F4B99',
          weight: 2,
          opacity: 1,
          fillOpacity: 1
        }).addTo(group);

        circle.bindPopup(`
          <div style="font-family: 'IBM Plex Sans', Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.4; color: #172033;">
            <strong>${st.station_name} [${st.station_id}]</strong><br/>
            Predicted ETA: <b>${st.predicted_arrival_time}</b><br/>
            Delay: +${st.predicted_delay_minutes} min<br/>
            Range: ${st.eta_lower_bound} – ${st.eta_upper_bound}
          </div>
        `);
      }
    });

    // Add current live train marker
    if (currentLat && currentLon) {
      const trainIcon = L.divIcon({
        className: 'clean-train-pin',
        html: `
          <div style="
            width: 22px;
            height: 22px;
            background: #102A56;
            border: 2px solid #FFFFFF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 1px 4px rgba(16,42,86,0.35);
          ">
            <span style="font-size: 11px; color: #FFFFFF;">🚆</span>
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      L.marker([currentLat, currentLon], { icon: trainIcon })
        .addTo(group)
        .bindPopup(`
          <div style="font-family: 'IBM Plex Sans', Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.4; color: #172033;">
            <strong>${liveState?.train_name || 'Train'}</strong><br/>
            Current Station: <b>${liveState?.current_station_name}</b><br/>
            Speed: <b>${liveState?.speed_kmph} km/h</b><br/>
            Status: <b>${liveState?.current_status === 'STOPPED_STATION' ? 'Stopped' : 'In transit'}</b>
          </div>
        `);
    }

    try {
      if (group.getLayers().length > 0) {
        map.fitBounds(group.getBounds(), { padding: [25, 25], maxZoom: 10 });
      }
    } catch (e) {
      // Graceful fallback
    }
  }, [trajectory, currentLat, currentLon, liveState?.current_status]);

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden h-full flex flex-col">
      {/* Subtle Blue-tinted Header */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 py-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#102A56]">
            Live route
          </h3>
          <p className="text-xs text-[#64748B]">
            Geographic path and real-time train positioning
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#64748B]">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#102A56] inline-block"></span> Train
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#1F4B99] inline-block border border-gray-300"></span> Halts
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-600 inline-block"></span> Destination
          </span>
        </div>
      </div>

      <div className="p-3 flex-1 flex flex-col">
        <div
          ref={mapContainerRef}
          className="w-full h-[320px] rounded-[8px] overflow-hidden border border-[#D9E2EC] bg-[#EEF3F8]"
        ></div>

        <div className="flex justify-between items-center text-xs text-[#64748B] mt-2">
          <span>OpenStreetMap network tiles</span>
          <span>Route: {trajectory.length} stations</span>
        </div>
      </div>
    </section>
  );
}
