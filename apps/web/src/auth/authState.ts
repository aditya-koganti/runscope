import { createContext, useContext } from "react";

export type Role = "viewer" | "researcher" | "administrator";

export interface User {
  id: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface AuthValue {
  user: User | null;
  accessToken: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

export const AuthContext = createContext<AuthValue | null>(null);

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
