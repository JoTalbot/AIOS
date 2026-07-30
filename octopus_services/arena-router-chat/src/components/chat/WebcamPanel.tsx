"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Camera, CameraOff, SwitchCamera, X, Maximize2 } from "lucide-react";

interface CapturedPhoto {
  id: string;
  dataUrl: string;
  timestamp: number;
}

interface WebcamPanelProps {
  onCapture?: (dataUrl: string) => void;
}

export function WebcamPanel({ onCapture }: WebcamPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [photos, setPhotos] = useState<CapturedPhoto[]>([]);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("user");
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState<string | null>(null);
  const [isMirrored, setIsMirrored] = useState(true);

  const startCamera = useCallback(async () => {
    try {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setStream(mediaStream);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Camera access denied"
      );
    }
  }, [facingMode, stream]);

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  }, [stream]);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (isMirrored) {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    const photo: CapturedPhoto = {
      id: Date.now().toString(),
      dataUrl,
      timestamp: Date.now(),
    };
    setPhotos((prev) => [photo, ...prev]);
    onCapture?.(dataUrl);
  };

  const switchCamera = () => {
    stopCamera();
    setFacingMode((prev) =>
      prev === "user" ? "environment" : "user"
    );
    setIsMirrored((prev) => !prev);
  };

  return (
    <>
      <div className="border-t border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="p-2.5 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${stream ? "bg-green-500 animate-pulse" : "bg-red-400"}`} />
              <span className="text-xs font-medium text-muted-foreground">
                Camera {stream ? "active" : "off"}
              </span>
            </div>
            <div className="flex items-center gap-0.5">
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                onClick={switchCamera}
                disabled={!!error}
                title="Switch camera"
              >
                <SwitchCamera className="w-3 h-3" />
              </Button>
            </div>
          </div>

          {/* Video feed */}
          <div className="relative rounded-lg overflow-hidden bg-black/90 aspect-video max-h-36 mx-auto max-w-sm">
            {error ? (
              <div className="flex items-center justify-center h-full text-xs text-destructive p-3 text-center">
                {error}
              </div>
            ) : (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${isMirrored ? "scale-x-[-1]" : ""}`}
              />
            )}
            {/* Capture overlay button */}
            <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2">
              <button
                onClick={capturePhoto}
                disabled={!!error || !stream}
                className="w-8 h-8 rounded-full bg-white/90 hover:bg-white border-2 border-gray-300 transition-all active:scale-90 disabled:opacity-40 flex items-center justify-center"
                title="Capture photo"
              >
                <Camera className="w-3.5 h-3.5 text-gray-700" />
              </button>
            </div>
          </div>

          {/* Captured photos strip */}
          {photos.length > 0 && (
            <div className="flex gap-1.5 overflow-x-auto pb-0.5">
              {photos.slice(0, 10).map((photo) => (
                <div
                  key={photo.id}
                  className="relative flex-shrink-0 w-12 h-9 rounded border border-border/50 cursor-pointer hover:border-primary/50 transition group"
                  onClick={() => setShowPreview(photo.dataUrl)}
                >
                  <img
                    src={photo.dataUrl}
                    alt=""
                    className="w-full h-full object-cover rounded"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Preview modal */}
      {showPreview && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setShowPreview(null)}
        >
          <div className="relative max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <img
              src={showPreview}
              alt="Captured"
              className="w-full rounded-lg shadow-2xl"
            />
            <Button
              size="icon"
              variant="secondary"
              className="absolute top-2 right-2 h-7 w-7"
              onClick={() => setShowPreview(null)}
            >
              <X className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" />
    </>
  );
}
