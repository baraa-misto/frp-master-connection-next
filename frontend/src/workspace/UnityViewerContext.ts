import { createContext, useContext } from "react";
import type { UnityView } from "./unityRatio";

export const UnityViewerContext = createContext<UnityView | null>(null);
export const useUnityViewer = () => useContext(UnityViewerContext);
