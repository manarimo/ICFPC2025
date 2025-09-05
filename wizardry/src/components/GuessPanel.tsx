'use client';

import { useState } from 'react';
import { GameState } from '@/types/api';
import { useBackend } from '@/contexts/BackendContext';

interface GuessPanelProps {
  gameState: GameState;
  onUpdateGameState?: (updates: Partial<GameState>) => void;
}

export function GuessPanel({ gameState, onUpdateGameState }: GuessPanelProps) {
  const { apiClient } = useBackend();
  const [numRooms, setNumRooms] = useState('1');
  const [roomInputs, setRoomInputs] = useState<string[]>(['']);
  const [startingRoom, setStartingRoom] = useState('0');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ correct: boolean; message: string } | null>(null);

  const handleNumRoomsChange = (value: string) => {
    const num = parseInt(value, 10);
    if (num > 0 && num <= 100) { // reasonable limit
      setNumRooms(value);
      const newRoomInputs = Array(num).fill('').map((_, i) => roomInputs[i] || '');
      setRoomInputs(newRoomInputs);
    }
  };

  const handleRoomInputChange = (roomIndex: number, value: string) => {
    const newRoomInputs = [...roomInputs];
    newRoomInputs[roomIndex] = value;
    setRoomInputs(newRoomInputs);
  };

  const parseAnswer = () => {
    const connections = [];
    const rooms = [];

    for (let roomIndex = 0; roomIndex < roomInputs.length; roomIndex++) {
      const roomInput = roomInputs[roomIndex].trim();
      if (!roomInput) continue;

      rooms.push(roomIndex);

      // Parse 6 pairs of (roomTo, doorTo)
      const pairRegex = /\(\s*(\d+)\s*,\s*(\d+)\s*\)/g;
      const pairs = [];
      let match;

      while ((match = pairRegex.exec(roomInput)) !== null) {
        pairs.push([parseInt(match[1], 10), parseInt(match[2], 10)]);
      }

      if (pairs.length !== 6) {
        throw new Error(`Room ${roomIndex}: Expected exactly 6 pairs of (roomTo, doorTo), found ${pairs.length}`);
      }

      // Create connections for each door of this room
      for (let doorIndex = 0; doorIndex < 6; doorIndex++) {
        const [toRoom, toDoor] = pairs[doorIndex];
        
        if (toDoor < 0 || toDoor > 5) {
          throw new Error(`Room ${roomIndex}, door ${doorIndex}: Invalid door number ${toDoor}. Must be 0-5.`);
        }

        connections.push({
          from: {
            room: roomIndex,
            door: doorIndex,
          },
          to: {
            room: toRoom,
            door: toDoor,
          }
        });
      }
    }

    return {
      rooms,
      connections,
      startingRoom: parseInt(startingRoom, 10)
    };
  };

  const handleGuess = async () => {
    if (roomInputs.every(input => !input.trim())) {
      setError('Please enter room connections');
      return;
    }

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const mapData = parseAnswer();
      
      const response = await apiClient.guess({
        id: gameState.teamId,
        map: mapData
      });

      setResult({
        correct: response.correct,
        message: response.correct 
          ? 'Congratulations! Your map is correct!' 
          : 'Your map is incorrect. Please try again.'
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while submitting your guess');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-4">Submit Your Map</h2>
      
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="numRooms" className="block text-sm font-medium text-gray-700 mb-1">
              Number of Rooms
            </label>
            <input
              type="number"
              id="numRooms"
              value={numRooms}
              onChange={(e) => handleNumRoomsChange(e.target.value)}
              min="1"
              max="100"
              className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
          </div>
          
          <div>
            <label htmlFor="startingRoom" className="block text-sm font-medium text-gray-700 mb-1">
              Starting Room
            </label>
            <input
              type="number"
              id="startingRoom"
              value={startingRoom}
              onChange={(e) => setStartingRoom(e.target.value)}
              min="0"
              className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium text-gray-700 mb-3">Room Connections</h3>
          <p className="text-sm text-gray-600 mb-4">
            For each room, enter 6 pairs of (roomTo, doorTo) - one for each door (0-5).
            Example: (1,2) (0,4) (3,1) (2,0) (1,3) (0,5)
          </p>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {roomInputs.map((roomInput, roomIndex) => (
              <div key={roomIndex} className="border rounded-md p-3 bg-gray-50">
                <label htmlFor={`room-${roomIndex}`} className="block text-sm font-medium text-gray-700 mb-2">
                  Room {roomIndex} - Door destinations (0→1→2→3→4→5):
                </label>
                <input
                  type="text"
                  id={`room-${roomIndex}`}
                  value={roomInput}
                  onChange={(e) => handleRoomInputChange(roomIndex, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="(1,2) (0,4) (3,1) (2,0) (1,3) (0,5)"
                  disabled={isLoading}
                />
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">{error}</div>
        )}

        {result && (
          <div className={`text-sm p-3 rounded-md ${
            result.correct 
              ? 'bg-green-50 text-green-700 border border-green-200' 
              : 'bg-yellow-50 text-yellow-700 border border-yellow-200'
          }`}>
            {result.message}
          </div>
        )}

        <button
          onClick={handleGuess}
          disabled={isLoading || roomInputs.every(input => !input.trim())}
          className="bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Submitting...' : 'Submit Map'}
        </button>
      </div>

      {gameState.explorationResults.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 mb-2">Tips for building your map:</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Use the exploration results above to understand the room structure</li>
            <li>• Each line represents a bidirectional connection between two doors</li>
            <li>• Make sure all rooms discovered during exploration are included</li>
            <li>• Verify that your connections form a valid undirected graph</li>
          </ul>
        </div>
      )}
    </div>
  );
}