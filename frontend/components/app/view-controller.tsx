'use client';

import { useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useRoomContext } from '@livekit/components-react';
import { useSession } from '@/components/session-provider';
import { SessionView } from '@/components/session-view';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(SessionView);

export function ViewController() {
  const room = useRoomContext();
  const { appConfig, isSessionActive, startSession } = useSession();

  return (
    <AnimatePresence mode="wait">
      {!isSessionActive && (
        <MotionWelcomeView
          key="welcome"
          startButtonText={appConfig.startButtonText}
          onStartCall={startSession}
        />
      )}

      {isSessionActive && (
        <MotionSessionView
          key="session"
          appConfig={appConfig}
        />
      )}
    </AnimatePresence>
  );
}
