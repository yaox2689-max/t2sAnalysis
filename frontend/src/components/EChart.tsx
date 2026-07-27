import React, { useRef, useEffect } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  CanvasRenderer,
]);

/** ECharts wrapper that auto-resizes and disposes on unmount. */
const EChart: React.FC<{ option: Record<string, unknown> }> = ({ option }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const instance = echarts.init(chartRef.current);
    instanceRef.current = instance;

    const ro = new ResizeObserver(() => instance.resize());
    ro.observe(chartRef.current);

    return () => {
      ro.disconnect();
      instance.dispose();
      instanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    instanceRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={chartRef}
      style={{
        width: "100%",
        height: 380,
        borderRadius: 10,
        overflow: "hidden",
      }}
    />
  );
};

export default EChart;
