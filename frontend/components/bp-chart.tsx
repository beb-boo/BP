"use client";

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ReferenceArea } from 'recharts';
import { useTheme } from "next-themes";
import { calculateAge, getBPLimits } from "@/lib/bp-standards";

interface BPRecord {
    measurement_date: string;
    measurement_time: string;
    systolic: number;
    diastolic: number;
    pulse: number;
}

interface BPChartProps {
    data: BPRecord[];
    userDob?: string; // Optional DOB to calculate limits
}

// Moved outside component to prevent re-creation on render
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-lg text-xs z-50">
                <p className="font-semibold mb-2">
                    {new Date(label).toLocaleDateString("en-GB", { day: 'numeric', month: 'short', year: 'numeric' })}
                </p>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {payload.map((entry: any, index: number) => (
                    <div key={index} className="flex items-center gap-2 mb-1" style={{ color: entry.color }}>
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span className="capitalize">{entry.name}:</span>
                        <span className="font-bold">{entry.value}</span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export function BPChart({ data, userDob }: BPChartProps) {
    const { theme } = useTheme();

    // Calculate Limits
    const age = calculateAge(userDob);
    const limits = getBPLimits(age);

    // Sort data by date ascending for the chart
    // Sort data by date ascending for the chart
    const chartData = [...data].sort((a, b) => {
        const dateA = new Date(`${a.measurement_date}T${a.measurement_time || '00:00'}`);
        const dateB = new Date(`${b.measurement_date}T${b.measurement_time || '00:00'}`);
        return dateA.getTime() - dateB.getTime();
    }).map(d => ({
        ...d,
        fullDate: `${d.measurement_date}`
    }));

    // Calculate Y-Axis Domain explicitly to ensure Reference Lines are visible
    const allValues = chartData.flatMap(d => [d.systolic, d.diastolic, d.pulse]);
    const dataMax = allValues.length > 0 ? Math.max(...allValues) : 0;
    const dataMin = allValues.length > 0 ? Math.min(...allValues) : 0;

    // Ensure domain includes the High BP Limits (Sys Max)
    const yMax = Math.max(dataMax + 10, limits.sysMax + 20);
    // Ensure domain includes lower values but not negative
    const yMin = Math.max(0, Math.min(dataMin - 10, 40));

    return (
        <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData} margin={{ top: 20, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={theme === 'dark' ? '#334155' : '#e2e8f0'} />
                <XAxis
                    dataKey="measurement_date"
                    tickFormatter={(str) => new Date(str).toLocaleDateString("en-GB", { day: 'numeric', month: 'numeric' })}
                    stroke="#94a3b8"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                />
                <YAxis
                    stroke="#94a3b8"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    domain={[yMin, yMax]}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '3 3' }} />
                <Legend />

                {/* Reference Areas (Zones) */}
                {/* High Diastolic Zone (e.g., 90 - 140) */}
                <ReferenceArea
                    y1={limits.diaMax}
                    y2={limits.sysMax}
                    fill="#ecfeff" // Cyan-50
                    fillOpacity={0.6}
                    label={{ value: "High Dia", position: 'insideTopLeft', fill: '#0891b2', fontSize: 10 }}
                />

                {/* High Systolic Zone (e.g., 140+) */}
                <ReferenceArea
                    y1={limits.sysMax}
                    y2={yMax}
                    fill="#fef2f2" // Red-50
                    fillOpacity={0.6}
                    label={{ value: "High Sys & Dia", position: 'insideTopLeft', fill: '#ef4444', fontSize: 10 }}
                />

                {/* Optional: Optimal Zone (< DiaMax) can be left clear or Green-50 (#f0fdf4) */}


                <Line
                    type="monotone"
                    dataKey="systolic"
                    name="Systolic"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#ef4444" }}
                    activeDot={{ r: 6 }}
                    isAnimationActive={false}
                />
                <Line
                    type="monotone"
                    dataKey="diastolic"
                    name="Diastolic"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#3b82f6" }}
                    activeDot={{ r: 6 }}
                    isAnimationActive={false}
                />
                <Line
                    type="monotone"
                    dataKey="pulse"
                    name="Pulse"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 3, fill: "#10b981" }}
                    activeDot={{ r: 5 }}
                    isAnimationActive={false}
                />
            </LineChart>
        </ResponsiveContainer>
    );
}
