
import {
  HttpErrorResponse,
  HttpInterceptorFn
} from '@angular/common/http';

import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from './auth.service';


export const authInterceptor: HttpInterceptorFn = (req, next) => {

  const auth = inject(AuthService);

  // Only handle requests to our FastAPI backend.
  if (!req.url.startsWith(auth.api + '/')) {
    return next(req);
  }

  // Login, refresh and logout manage their own authentication.
  const isAuthEndpoint = [
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/logout'
  ].some(path => req.url === auth.api + path);

  if (isAuthEndpoint) {
    return next(req);
  }

  const token = auth.token;

  const authenticatedRequest = token
    ? req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      })
    : req;

  return next(authenticatedRequest).pipe(
    catchError((error: HttpErrorResponse) => {

      // Only refresh on authentication failures.
      if (
        error.status !== 401 ||
        !auth.hasTabSession
      ) {
        return throwError(() => error);
      }

      return auth.refresh().pipe(
        switchMap(newToken => {

          const retryRequest = req.clone({
            setHeaders: {
              Authorization: `Bearer ${newToken}`
            }
          });

          return next(retryRequest);
        }),
        catchError(refreshError => {
          if (
            refreshError instanceof HttpErrorResponse &&
            refreshError.status === 401
          ) {
            auth.clearLocalSession();
          }

          return throwError(() => refreshError);
        })
      );
    })
  );
};
