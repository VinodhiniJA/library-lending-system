
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  Observable,
  finalize,
  map,
  shareReplay,
  tap
} from 'rxjs';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  readonly api = 'http://localhost:8000';

  private accessToken = '';
  private refreshRequest$?: Observable<string>;

  private readonly sessionKey = 'library_tab_session';

  constructor(private http: HttpClient) {
    // Remove credentials from the previous implementation.
    localStorage.removeItem('token');
    localStorage.removeItem('role');
  }

  get token(): string {
    return this.accessToken;
  }

  get hasTabSession(): boolean {
    return sessionStorage.getItem(this.sessionKey) === 'active';
  }

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(
      `${this.api}/auth/login`,
      { email, password },
      { withCredentials: true }
    ).pipe(
      tap(response => {
        this.accessToken = response.access_token;
        sessionStorage.setItem(this.sessionKey, 'active');
      })
    );
  }

  refresh(): Observable<string> {
    if (!this.refreshRequest$) {
      this.refreshRequest$ = this.http.post<TokenResponse>(
        `${this.api}/auth/refresh`,
        {},
        { withCredentials: true }
      ).pipe(
        map(response => response.access_token),
        tap(token => {
          this.accessToken = token;
        }),
        finalize(() => {
          this.refreshRequest$ = undefined;
        }),
        shareReplay({ bufferSize: 1, refCount: false })
      );
    }

    return this.refreshRequest$;
  }

  restoreSession(): Observable<string> {
    return this.refresh();
  }

  logout(): Observable<any> {
    // Clear the frontend session immediately.
    this.clearLocalSession();

    return this.http.post(
      `${this.api}/auth/logout`,
      {},
      { withCredentials: true }
    );
  }

  clearLocalSession(): void {
    this.accessToken = '';
    sessionStorage.removeItem(this.sessionKey);
    localStorage.removeItem('token');
    localStorage.removeItem('role');
  }
}
