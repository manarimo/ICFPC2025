import { SelectRequest, SelectResponse, ExploreRequest, ExploreResponse, GuessRequest, GuessResponse } from '@/types/api';
import { BackendType } from '@/contexts/BackendContext';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://icfpcontest2025.github.io';

export class ApiClient {
  private backendType: BackendType = 'mock';

  setBackendType(type: BackendType) {
    this.backendType = type;
  }

  private async makeRequest<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-backend-type': this.backendType,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async select(request: SelectRequest): Promise<SelectResponse> {
    return this.makeRequest<SelectResponse>('/select', request);
  }

  async explore(request: ExploreRequest): Promise<ExploreResponse> {
    return this.makeRequest<ExploreResponse>('/explore', request);
  }

  async guess(request: GuessRequest): Promise<GuessResponse> {
    return this.makeRequest<GuessResponse>('/guess', request);
  }
}

export const apiClient = new ApiClient();