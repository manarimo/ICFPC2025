'use client';

import { useState, useEffect } from 'react';
import { GameState } from '@/types/api';
import { SessionSetup } from '@/components/SessionSetup';
import { ExplorePanel } from '@/components/ExplorePanel';
import { GuessPanel } from '@/components/GuessPanel';
import { storage } from '@/lib/storage';

export default function Home() {
  const [gameState, setGameState] = useState<GameState | null>(null);

  useEffect(() => {
    // Try to restore game state from local storage
    const savedGameState = storage.getGameState();
    if (savedGameState) {
      setGameState(savedGameState);
    }
  }, []);

  const handleSessionStart = (teamId: string, problemName: string) => {
    const newGameState: GameState = {
      teamId,
      problemName,
      queryCount: 0,
      explorationResults: []
    };
    setGameState(newGameState);
    storage.setGameState(newGameState);
  };

  const updateGameState = (updates: Partial<GameState>) => {
    if (gameState) {
      const updatedGameState = { ...gameState, ...updates };
      setGameState(updatedGameState);
      storage.setGameState(updatedGameState);
    }
  };

  const handleClearSession = () => {
    storage.clearAll();
    setGameState(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-900">
          ICFP 2025 Library Mapping Tool
        </h1>
        
        {!gameState ? (
          <SessionSetup onSessionStart={handleSessionStart} />
        ) : (
          <div className="space-y-8">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex justify-between items-start mb-2">
                <h2 className="text-xl font-semibold">Session Info</h2>
                <button
                  onClick={handleClearSession}
                  className="text-sm bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-md transition-colors"
                >
                  Clear Session
                </button>
              </div>
              <p><strong>Team ID:</strong> {gameState.teamId}</p>
              <p><strong>Problem:</strong> {gameState.problemName}</p>
              <p><strong>Query Count:</strong> {gameState.queryCount}</p>
            </div>
            
            <ExplorePanel 
              gameState={gameState} 
              onUpdateGameState={updateGameState} 
            />
            
            <GuessPanel 
              gameState={gameState} 
              onUpdateGameState={updateGameState} 
            />
          </div>
        )}
      </div>
    </div>
  );
}
