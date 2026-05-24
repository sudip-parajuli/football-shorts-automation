import React, { useMemo } from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';

export interface DataPoint {
  label: string;
  value: number;
}

export interface DataVisualizationSceneProps {
  title?: string;
  chartType: "bar_chart" | "line_chart";
  data: DataPoint[];
}

export const DataVisualizationScene: React.FC<DataVisualizationSceneProps> = ({
  title = "DATA VIZ",
  chartType = "bar_chart",
  data = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animate the data so bars/lines grow over time
  const animatedData = useMemo(() => {
    return data.map((d, i) => {
      const delay = i * 5; // stagger
      const p = spring({
        frame: Math.max(0, frame - delay),
        fps,
        config: { damping: 14, stiffness: 80, mass: 0.8 },
      });
      return {
        ...d,
        value: d.value * p,
      };
    });
  }, [data, frame, fps]);

  const progress = spring({
    frame,
    fps,
    config: { damping: 14 },
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0A0A12',
        padding: '80px 100px',
        fontFamily: 'Barlow Condensed, sans-serif',
      }}
    >
      <div
        style={{
          fontSize: '48px',
          fontWeight: 700,
          color: '#FFFFFF',
          textTransform: 'uppercase',
          letterSpacing: '4px',
          marginBottom: '40px',
          textAlign: 'center',
          opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' }),
          transform: `translateY(${interpolate(frame, [0, 10], [20, 0], { extrapolateRight: 'clamp' })}px)`,
        }}
      >
        {title}
      </div>

      <div style={{ flex: 1, width: '100%', height: '100%', opacity: progress }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar_chart' ? (
            <BarChart data={animatedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
              <XAxis dataKey="label" stroke="#AAA" tick={{ fill: '#AAA', fontSize: 24 }} axisLine={false} tickLine={false} />
              <YAxis stroke="#AAA" tick={{ fill: '#AAA', fontSize: 24 }} axisLine={false} tickLine={false} />
              <Bar dataKey="value" fill="#F5A623" isAnimationActive={false} radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : (
            <LineChart data={animatedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
              <XAxis dataKey="label" stroke="#AAA" tick={{ fill: '#AAA', fontSize: 24 }} axisLine={false} tickLine={false} />
              <YAxis stroke="#AAA" tick={{ fill: '#AAA', fontSize: 24 }} axisLine={false} tickLine={false} />
              <Line type="monotone" dataKey="value" stroke="#F5A623" strokeWidth={6} dot={{ r: 6, fill: '#F5A623', stroke: '#C0392B', strokeWidth: 2 }} isAnimationActive={false} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </AbsoluteFill>
  );
};
