export interface SelectRequest {
  id: string;
  problemName: string;
}

export interface SelectResponse {
  problemName: string;
}

export interface ExploreRequest {
  id: string;
  plans: string[];
}

export interface ExploreResponse {
  results: number[][];
  queryCount: number;
}

export interface GuessRequest {
  id: string;
  map: {
    rooms: number[];
    startingRoom: number;
    connections: Array<
      {
        from: {
          room: number,
          door: number,
        },
        to: {
          room: number,
          door: number,
        }
      }>;
  };
}

export interface GuessResponse {
  correct: boolean;
}

export interface SpoilerRequest {
  id: string;
}

export interface SpoilerResponse {
  map: {
    rooms: number[];
    startingRoom: number;
    connections: Array<
      {
        from: { room: number, door: number },
        to: { room: number, door: number }
      }
    >;
  };
}

export interface GameState {
  teamId: string;
  problemName: string;
  queryCount: number;
  explorationResults: Array<{
    routePlan: number[];
    roomLabels: number[];
  }>;
}
