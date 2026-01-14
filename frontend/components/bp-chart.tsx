"use client"

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useTheme } from "next-themes";

interface BPRecord {
    measurement_date: string;
    measurement_time: string;
    systolic: number;
    diastolic: number;
    pulse: number;
}

interface BPChartProps {
    data: BPRecord[];
}

// Moved outside component to prevent re-creation on render
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-lg text-xs">
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

export function BPChart({ data }: BPChartProps) {
    const { theme } = useTheme();

    // Sort data by date ascending for the chart
    const chartData = [...data].sort((a, b) => {
        const dateA = new Date(`${a.measurement_date}T${a.measurement_time || '00:00'}`);
        const dateB = new Date(`${b.measurement_date}T${b.measurement_time || '00:00'}`);
        return dateA.getTime() - dateB.getTime();
    }).map(d => ({
        ...d,
        fullDate: `${d.measurement_date}`
    }));

    return (
        <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
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
                    domain={['dataMin - 10', 'dataMax + 10']}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line
                    type="monotone"
                    dataKey="systolic"
                    name="Systolic"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#ef4444" }}
                    activeDot={{ r: 6 }}
                />
                <Line
                    type="monotone"
                    dataKey="diastolic"
                    name="Diastolic"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#3b82f6" }}
                    activeDot={{ r: 6 }}
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
                />
            </LineChart>
        </ResponsiveContainer>
    );
}
