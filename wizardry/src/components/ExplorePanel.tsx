'use client';

import { useState } from 'react';
import { GameState } from '@/types/api';
import { apiClient } from '@/lib/api';

interface ExplorePanelProps {
  gameState: GameState;
  onUpdateGameState: (updates: Partial<GameState>) => void;
}

export function ExplorePanel({ gameState, onUpdateGameState }: ExplorePanelProps) {
  const [routeInput, setRouteInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Calculate character counts for each line
  const getLineCounts = (): Array<{ line: string, count: number }> => {
    return routeInput
      .split('\n')
      .map(line => ({
        line: line,
        count: line.trim().length
      }));
  };

  const parseRouteInput = (input: string): { plans: string[], routePlans: number[][] } => {
    const lines = input
      .trim()
      .split('\n')
      .filter(line => line.trim());

    const plans: string[] = [];
    const routePlans: number[][] = [];

    for (const line of lines) {
      const trimmedLine = line.trim();
      // Validate that each character is a digit 0-5
      if (!/^[0-5]+$/.test(trimmedLine)) {
        throw new Error(`Invalid route: "${trimmedLine}". Must contain only digits 0-5.`);
      }
      
      plans.push(trimmedLine);
      routePlans.push(trimmedLine.split('').map(d => parseInt(d, 10)));
    }

    return { plans, routePlans };
  };

  const handleExplore = async () => {
    if (!routeInput.trim()) {
      setError('Please enter at least one route');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const { plans, routePlans } = parseRouteInput(routeInput);
      
      const response = await apiClient.explore({
        id: gameState.teamId,
        plans: plans,
      });

      const newResults = routePlans.map((routePlan, index) => ({
        routePlan,
        roomLabels: response.results[index] || []
      }));

      onUpdateGameState({
        queryCount: response.queryCount,
        explorationResults: [...gameState.explorationResults, ...newResults]
      });

      setRouteInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during exploration');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-4">Explore Routes</h2>
      
      <div className="space-y-4">
        <div>
          <label htmlFor="routes" className="block text-sm font-medium text-gray-700 mb-2">
            Route Plans (one per line, consecutive door numbers 0-5)
          </label>
          <div className="flex gap-4">
            <div className="flex-1">
              <textarea
                id="routes"
                value={routeInput}
                onChange={(e) => setRouteInput(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                placeholder=""
                disabled={isLoading}
              />
              <p className="text-sm text-gray-600 mt-1">
                Example: &quot;012&quot; means go through door 0, then door 1, then door 2
              </p>
            </div>
            
            {routeInput && (
              <div className="w-48 bg-gray-50 p-3 rounded-md border">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Character Count per Line</h4>
                <div className="space-y-1 text-xs font-mono max-h-32 overflow-y-auto">
                  {getLineCounts().map((item, index) => (
                    <div key={index} className="flex justify-between">
                      <span className="text-gray-600 truncate mr-2">
                        {item.line || '(empty)'}
                      </span>
                      <span className={`font-bold ${item.count === 0 ? 'text-gray-400' : 'text-blue-600'}`}>
                        {item.count}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <div className="text-xs text-gray-600">
                    <div>Total lines: {getLineCounts().length}</div>
                    <div>Non-empty: {getLineCounts().filter(item => item.count > 0).length}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}

        <button
          onClick={handleExplore}
          disabled={isLoading || !routeInput.trim()}
          className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Exploring...' : 'Explore Routes'}
        </button>
      </div>

      {gameState.explorationResults.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Exploration Results</h3>
          <div className="space-y-6">
            {gameState.explorationResults.map((result, resultIndex) => {
              // Prepend START action to align with starting room
              // First room label is the starting room, then each door action leads to next room
              const actionsWithStart = ['START', ...result.routePlan.map(door => `${door}`)];
              const roomLabels = result.roomLabels;
              
              const maxLength = Math.max(actionsWithStart.length, roomLabels.length);
              const zippedResults = Array.from({ length: maxLength }, (_, i) => ({
                step: i + 1,
                action: actionsWithStart[i] || '—',
                outcome: roomLabels[i] !== undefined ? `${roomLabels[i]}` : '—',
                hasAction: actionsWithStart[i] !== undefined,
                hasOutcome: roomLabels[i] !== undefined,
                isStart: i === 0
              }));

              return (
                <div key={resultIndex} className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-blue-50 px-4 py-2 border-b border-gray-200">
                    <h4 className="text-sm font-medium text-blue-900">
                      Route {resultIndex + 1}: {result.routePlan.join('')} 
                      <span className="text-blue-600 ml-2">({result.routePlan.length} steps)</span>
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <div className="bg-blue-50 px-4 py-2 border-b border-gray-200">
                      <span className="text-sm font-medium text-blue-900">Raw:</span>
                      <input 
                        type="text" 
                        readOnly 
                        value={JSON.stringify(result.roomLabels)} 
                        onClick={(e) => {
                          navigator.clipboard.writeText(e.currentTarget.value);
                          // Optional: Add visual feedback
                          e.currentTarget.select();
                        }}
                        className="ml-2 px-2 py-1 bg-white border border-gray-300 rounded text-sm font-mono cursor-pointer hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        title="Click to copy to clipboard"
                      />
                    </div>
                    <table className="min-w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                            Step
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Action
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Outcome
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {zippedResults.map((row, rowIndex) => (
                          <tr key={rowIndex} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-sm text-gray-900 font-mono">
                              {row.step}
                            </td>
                            <td className={`px-3 py-2 text-sm font-mono ${
                              row.isStart ? 'text-purple-600 font-medium' : 
                              row.hasAction ? 'text-blue-600 font-medium' : 'text-gray-400'
                            }`}>
                              {row.action}
                            </td>
                            <td className={`px-3 py-2 text-sm font-mono ${
                              row.hasOutcome ? 'text-green-600 font-medium' : 'text-gray-400'
                            }`}>
                              {row.outcome}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}