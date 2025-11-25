'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { ChatTranscript } from '@/components/app/chat-transcript';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { TileLayout } from '@/components/app/tile-layout';
import {
  AgentControlBar,
  type ControlBarControls,
} from '@/components/livekit/agent-control-bar/agent-control-bar';
import { useChatMessages } from '@/hooks/useChatMessages';
import { useConnectionTimeout } from '@/hooks/useConnectionTimout';
import { useDebugMode } from '@/hooks/useDebug';
import { cn } from '@/lib/utils';

import { useRoomContext } from '@livekit/components-react';
import WellnessSummary from '@/components/WellnessSummary';

const MotionBottom = motion.create('div');

interface SessionViewProps {
  appConfig: AppConfig;
}

export const SessionView = ({
  appConfig,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {

  const room = useRoomContext();
  const messages = useChatMessages();
  const [chatOpen, setChatOpen] = useState(false);
  const [wellness, setWellness] = useState(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // -------------------------
  // LISTEN TO BACKEND EVENTS
  // -------------------------
  useEffect(() => {
    if (!room) return;

    const listener = (payload: any) => {
      try {
        const decoded = new TextDecoder().decode(payload.data);
        const msg = JSON.parse(decoded);

        if (msg.type !== 'wellness_update') return;

        console.log("WELLNESS:", msg.data);
        setWellness(msg.data);

      } catch (err) {
        console.error(err);
      }
    };

    room.on('dataReceived', listener);
    return () => { room.off('dataReceived', listener); };
  }, [room]);

  // Controls at bottom
  const controls: ControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: false,
    screenShare: false,
  };

  // AI Listening Indicator
  const isListening = (room as any)?.connectionState === "connected";

  return (
    <section
      className="relative h-full w-full overflow-hidden bg-gradient-to-b from-[#0f1115] to-[#0b0d11] text-white"
      {...props}
    >

      {/* AI LISTENING INDICATOR */}
      <div className="w-full flex justify-center mt-4 mb-2">
        <div className="flex items-center gap-2">
          <span
            className={`h-3 w-3 rounded-full transition-all ${
              isListening ? "bg-green-400 animate-pulse" : "bg-gray-500"
            }`}
          ></span>
          <span className="text-sm text-gray-300">
            {isListening ? "AI is listening…" : "Connecting…"}
          </span>
        </div>
      </div>

      {/* WELLNESS CARD UI */}
      <div className="flex justify-center mt-4">
        <WellnessSummary entry={wellness} />
      </div>

      {/* CHAT TRANSCRIPT */}
      <div
        className={cn(
          "fixed inset-0 grid grid-cols-1 grid-rows-1 transition-opacity",
          !chatOpen && "pointer-events-none opacity-0"
        )}
      >
        <div
          ref={scrollRef}
          className="px-4 pt-40 pb-[150px] overflow-y-auto"
        >
          <ChatTranscript hidden={!chatOpen} messages={messages} />
        </div>
      </div>

      {/* TILE LAYOUT */}
      <TileLayout chatOpen={chatOpen} />

      {/* Bottom bar */}
      <MotionBottom
        initial={{ opacity: 0, translateY: "100%" }}
        animate={{ opacity: 1, translateY: "0%" }}
        exit={{ opacity: 0, translateY: "100%" }}
        transition={{ duration: 0.4 }}
        className="fixed inset-x-3 bottom-0 z-50"
      >
        <div className="bg-[#0d0f13]/70 backdrop-blur-xl rounded-xl pb-4 mx-auto max-w-2xl">
          <AgentControlBar controls={controls} onChatOpenChange={setChatOpen} />
        </div>
      </MotionBottom>

    </section>
  );
};
