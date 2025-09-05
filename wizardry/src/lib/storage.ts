import { GameState } from '@/types/api';

const STORAGE_KEYS = {
  TEAM_ID: 'icfp_team_id',
  PROBLEM_NAME: 'icfp_problem_name',
  GAME_STATE: 'icfp_game_state'
} as const;

export const storage = {
  getTeamId: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEYS.TEAM_ID);
  },

  setTeamId: (teamId: string): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEYS.TEAM_ID, teamId);
  },

  getProblemName: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEYS.PROBLEM_NAME);
  },

  setProblemName: (problemName: string): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEYS.PROBLEM_NAME, problemName);
  },

  getGameState: (): GameState | null => {
    if (typeof window === 'undefined') return null;
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.GAME_STATE);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  },

  setGameState: (gameState: GameState): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEYS.GAME_STATE, JSON.stringify(gameState));
  },

  clearAll: (): void => {
    if (typeof window === 'undefined') return;
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  }
};