import { mountApplication } from "./app/mountApplication";
import "./styles.css";

export const applicationRoot = mountApplication(document.getElementById("root"));
