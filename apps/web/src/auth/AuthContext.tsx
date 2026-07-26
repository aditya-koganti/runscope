import { useCallback, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { apiRequest } from "../api/client";
import { AuthContext } from "./authState";
import type { User } from "./authState";

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const signIn = useCallback(async (email: string, password: string) => {
    const response = await apiRequest<TokenResponse>("/auth/sign-in", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(response.access_token);
    setUser(response.user);
  }, []);

  const signOut = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, accessToken, signIn, signOut }),
    [accessToken, signIn, signOut, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
