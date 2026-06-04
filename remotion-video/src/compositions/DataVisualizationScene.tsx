import React, { useMemo } from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';

export interface DataPoint {
  label: string;
  value: number;
}

export interface LeaderboardEntry {
  rank: number;
  name: string;
  club: string;
  value: number;
  unit?: string;
}

export interface HeadToHeadData {
  playerA: { name: string; value: number; color: string };
  playerB: { name: string; value: number; color: string };
  metric: string;
}

export interface TimelinePoint {
  year: number;
  value: number;
  event?: string;
}

export interface DataVisualizationSceneProps {
  title?: string;
  chartType: "bar_chart" | "line_chart" | "leaderboard" | "head_to_head" | "timeline";
  data?: DataPoint[];
  leaderboard_data?: LeaderboardEntry[];
  head_to_head_data?: HeadToHeadData;
  timeline_data?: TimelinePoint[];
  timeline_title?: string;
}

export const DataVisualizationScene: React.FC<DataVisualizationSceneProps> = ({
  title = "DATA VIZ",
  chartType = "bar_chart",
  data = [],
  leaderboard_data = [],
  head_to_head_data,
  timeline_data = [],
  timeline_title = "",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 1. Staggered springs for leaderboard
  const leaderboardSprings = useMemo(() => {
    return leaderboard_data.map((_, i) => {
      const delay = i * 6; // stagger by 6 frames
      return spring({
        frame: Math.max(0, frame - delay),
        fps,
        config: { damping: 15, stiffness: 100 },
      });
    });
  }, [leaderboard_data, frame, fps]);

  // 2. Dual springs for head to head
  const pA = spring({ frame: Math.max(0, frame - 5), fps, config: { damping: 15, stiffness: 80 } });
  const pB = spring({ frame: Math.max(0, frame - 10), fps, config: { damping: 15, stiffness: 80 } });

  // 3. Staggered timeline points
  const animatedTimelineData = useMemo(() => {
    return timeline_data.map((d, i) => {
      const delay = 10 + i * 8;
      const p = spring({
        frame: Math.max(0, frame - delay),
        fps,
        config: { damping: 15, stiffness: 90 },
      });
      return {
        label: d.year.toString(),
        value: d.value,
        opacity: p,
        animatedValue: d.value * p,
        event: d.event,
      };
    });
  }, [timeline_data, frame, fps]);

  // Original growing animation for simple charts
  const animatedData = useMemo(() => {
    return data.map((d, i) => {
      const delay = i * 5;
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
        padding: '60px 80px',
        fontFamily: 'Barlow Condensed, sans-serif',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: '44px',
          fontWeight: 700,
          color: '#FFFFFF',
          textTransform: 'uppercase',
          letterSpacing: '4px',
          marginBottom: '30px',
          textAlign: 'center',
          opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' }),
          transform: `translateY(${interpolate(frame, [0, 10], [20, 0], { extrapolateRight: 'clamp' })}px)`,
        }}
      >
        {chartType === 'head_to_head' && head_to_head_data ? head_to_head_data.metric : chartType === 'timeline' ? timeline_title || title : title}
      </div>

      <div style={{ flex: 1, width: '100%', height: '100%', opacity: progress, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {chartType === 'leaderboard' ? (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%' }}>
            {leaderboard_data.slice(0, 5).map((entry, idx) => {
              const p = leaderboardSprings[idx] || 0;
              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '18px 30px',
                    margin: '10px 0',
                    backgroundColor: '#16162a',
                    borderRadius: '10px',
                    borderLeft: '6px solid #F5A623',
                    transform: `translateX(${(p - 1) * 100}%)`,
                    opacity: p,
                    fontSize: '26px',
                    fontWeight: 600,
                    color: '#FFFFFF',
                  }}
                >
                  <span style={{ color: '#F5A623', marginRight: '20px', width: '35px' }}>#{entry.rank || (idx + 1)}</span>
                  <span style={{ flex: 1 }}>{entry.name}</span>
                  <span style={{ color: '#AAA', marginRight: '30px', fontSize: '22px' }}>{entry.club}</span>
                  <span style={{ color: '#F5A623', fontWeight: 700 }}>
                    {Math.round(entry.value * p)} {entry.unit || 'goals'}
                  </span>
                </div>
              );
            })}
          </div>
        ) : chartType === 'head_to_head' && head_to_head_data ? (
          <div style={{ display: 'flex', width: '100%', height: '70%', alignItems: 'center', position: 'relative' }}>
            {/* Player A (Left) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', paddingRight: '40px' }}>
              <div style={{ fontSize: '42px', fontWeight: 700, color: '#FFFFFF', marginBottom: '15px' }}>{head_to_head_data.playerA.name}</div>
              <div style={{
                width: `${pA * 85}%`,
                height: '55px',
                backgroundColor: head_to_head_data.playerA.color === 'red' ? '#E74C3C' : head_to_head_data.playerA.color === 'amber' ? '#F5A623' : '#1ABC9C',
                borderRadius: '8px 0 0 8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                paddingRight: '20px',
              }}>
                <span style={{ color: '#000000', fontSize: '28px', fontWeight: 700 }}>
                  {Math.round(head_to_head_data.playerA.value * pA)}
                </span>
              </div>
            </div>
            
            {/* Middle Divider */}
            <div style={{ width: '4px', height: '100%', backgroundColor: '#FFFFFF', opacity: 0.8 }} />
            
            {/* Player B (Right) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', paddingLeft: '40px' }}>
              <div style={{ fontSize: '42px', fontWeight: 700, color: '#FFFFFF', marginBottom: '15px' }}>{head_to_head_data.playerB.name}</div>
              <div style={{
                width: `${pB * 85}%`,
                height: '55px',
                backgroundColor: head_to_head_data.playerB.color === 'red' ? '#E74C3C' : head_to_head_data.playerB.color === 'amber' ? '#F5A623' : '#1ABC9C',
                borderRadius: '0 8px 8px 0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-start',
                paddingLeft: '20px',
              }}>
                <span style={{ color: '#000000', fontSize: '28px', fontWeight: 700 }}>
                  {Math.round(head_to_head_data.playerB.value * pB)}
                </span>
              </div>
            </div>
          </div>
        ) : chartType === 'timeline' ? (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={animatedTimelineData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                  <XAxis dataKey="label" stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                  <YAxis stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                  <Line type="monotone" dataKey="animatedValue" stroke="#F5A623" strokeWidth={6} dot={{ r: 6, fill: '#F5A623', stroke: '#C0392B', strokeWidth: 2 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            {/* Event Display */}
            <div style={{ marginTop: '20px', height: '60px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {animatedTimelineData.map((d, idx) => {
                if (!d.event || d.opacity < 0.5) return null;
                // Only show the latest active event
                const isLatest = idx === animatedTimelineData.filter(pt => pt.opacity >= 0.5).length - 1;
                if (!isLatest) return null;
                return (
                  <div key={idx} style={{ color: '#F5A623', fontSize: '26px', fontWeight: 600, textAlign: 'center' }}>
                    {d.label}: {d.event}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'bar_chart' ? (
              <BarChart data={animatedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="label" stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                <Bar dataKey="value" fill="#F5A623" isAnimationActive={false} radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : (
              <LineChart data={animatedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="label" stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#AAA" tick={{ fill: '#AAA', fontSize: 22 }} axisLine={false} tickLine={false} />
                <Line type="monotone" dataKey="value" stroke="#F5A623" strokeWidth={6} dot={{ r: 6, fill: '#F5A623', stroke: '#C0392B', strokeWidth: 2 }} isAnimationActive={false} />
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </div>
    </AbsoluteFill>
  );
};
