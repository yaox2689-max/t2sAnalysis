import { useState, useRef, useCallback } from "react";
import { message } from "antd";
import { uploadDataset, deleteDataset, DatasetPreview } from "../services/api";

/**
 * Manages file upload state, drag-drop handlers, and dataset list.
 *
 * @param sessionIdRef - ref holding the current session id
 */
export function useFileUpload(
  sessionIdRef: React.MutableRefObject<string | null>,
) {
  const [datasets, setDatasets] = useState<DatasetPreview[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(
    async (file: File) => {
      const sid = sessionIdRef.current;
      if (!sid || uploading) return;

      setUploading(true);
      try {
        const res = await uploadDataset(file, sid);
        setDatasets((prev) => [...prev, ...res.datasets]);
        message.success(`已导入 ${res.count} 个数据集`);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "上传失败";
        message.error(msg);
      } finally {
        setUploading(false);
      }
    },
    [uploading, sessionIdRef],
  );

  const handleRemoveDataset = useCallback(async (tableName: string) => {
    try {
      await deleteDataset(tableName);
      setDatasets((prev) => prev.filter((d) => d.table_name !== tableName));
    } catch {
      message.error("删除失败");
    }
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileUpload(file);
        e.target.value = "";
      }
    },
    [handleFileUpload],
  );

  // Drag-drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) {
        handleFileUpload(file);
      }
    },
    [handleFileUpload],
  );

  return {
    datasets,
    uploading,
    dragging,
    fileInputRef,
    handleFileUpload,
    handleRemoveDataset,
    handleFileInputChange,
    handleDragOver,
    handleDragLeave,
    handleDrop,
  };
}
