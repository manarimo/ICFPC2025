'use client';

import { useState, useEffect } from 'react';
import { GameState } from '@/types/api';
import { SessionSetup } from '@/components/SessionSetup';
import { ExplorePanel } from '@/components/ExplorePanel';
import { GuessPanel } from '@/components/GuessPanel';
import { BackendToggle } from '@/components/BackendToggle';
import { storage } from '@/lib/storage';
import { useBackend } from '@/contexts/BackendContext';
import type { SpoilerResponse } from '@/types/api';

export default function Home() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const { apiClient } = useBackend();
  const [spoiler, setSpoiler] = useState<SpoilerResponse['map'] | null>(null);
  const [spoilerLoading, setSpoilerLoading] = useState(false);
  const [spoilerError, setSpoilerError] = useState('');

  const formatSpoilerConnections = (map: SpoilerResponse['map']): string[] => {
    const numRooms = map.rooms.length;
    const table: Array<Array<[number, number] | null>> = Array.from({ length: numRooms }, () => Array(6).fill(null));
    for (const conn of map.connections) {
      const fr = conn.from.room, fd = conn.from.door;
      const tr = conn.to.room, td = conn.to.door;
      if (table[fr]) table[fr][fd] = [tr, td];
      if (table[tr]) table[tr][td] = [fr, fd];
    }
    const lines: string[] = [];
    for (let room = 0; room < numRooms; room++) {
      const parts: string[] = [];
      for (let door = 0; door < 6; door++) {
        const dest = table[room][door];
        parts.push(dest ? `(${dest[0]},${dest[1]})` : `(?,?)`);
      }
      lines.push(`Room ${room} (${map.rooms[room]}): ${parts.join(' ')}`);
    }
    return lines;
  };

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
    setSpoiler(null);
    setSpoilerError('');
  };

  const handleShowSpoiler = async () => {
    if (!gameState) return;
    setSpoilerLoading(true);
    setSpoilerError('');
    try {
      const res = await apiClient.spoiler({ id: gameState.teamId });
      setSpoiler(res.map);
    } catch (e) {
      setSpoiler(null);
      setSpoilerError(e instanceof Error ? e.message : 'Failed to fetch spoiler');
    } finally {
      setSpoilerLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-900">
          ICFP 2025 Library Mapping Tool
        </h1>
        
        <BackendToggle />
        
        {!gameState ? (
          <SessionSetup onSessionStart={handleSessionStart} />
        ) : (
          <div className="space-y-8">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex justify-between items-start mb-2">
                <h2 className="text-xl font-semibold">Session Info</h2>
                <div className="flex gap-2">
                  <button
                    onClick={handleShowSpoiler}
                    className="text-sm bg-yellow-100 hover:bg-yellow-200 text-yellow-800 px-3 py-1 rounded-md transition-colors"
                    disabled={spoilerLoading}
                  >
                    {spoilerLoading ? 'Showing…' : 'Show Spoiler'}
                  </button>
                  <button
                    onClick={handleClearSession}
                    className="text-sm bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-md transition-colors"
                  >
                    Clear Session
                  </button>
                </div>
              </div>
              <p><strong>Team ID:</strong> {gameState.teamId}</p>
              <p><strong>Problem:</strong> {gameState.problemName}</p>
              <p><strong>Query Count:</strong> {gameState.queryCount}</p>
              {(spoilerError || spoiler) && (
                <div className="mt-3">
                  {spoilerError && (
                    <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
                      {spoilerError}
                    </div>
                  )}
                  {spoiler && (
                    <div className="mt-2">
                      <h2>Spoiler</h2>
                      <div className="text-sm font-medium text-gray-700">Starting room: {spoiler.startingRoom}</div>
                      <div className="mt-2">
                        <textarea
                          readOnly
                          value={formatSpoilerConnections(spoiler).map((line, idx) => line).join('\n')}
                          className="mt-1 w-full px-2 py-2 bg-gray-50 border border-gray-200 rounded text-xs font-mono max-h-64 overflow-auto focus:outline-none"
                          rows={Math.min(formatSpoilerConnections(spoiler).length, 12)}
                          onClick={(e) => {
                            navigator.clipboard.writeText(e.currentTarget.value);
                            e.currentTarget.select();
                          }}
                          title="Click to copy"
                        />
                        <p className="text-xs text-gray-500 mt-1">One line per room: (roomTo,doorTo) repeated for doors 0→1→2→3→4→5</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
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
