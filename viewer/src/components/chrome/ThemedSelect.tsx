import { Select } from "@openaec/ui-react";
import type { CSSProperties } from "react";
interface ThemedSelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  style?: CSSProperties;
}
export default function ThemedSelect({ onChange, ...props }: ThemedSelectProps) {
  return <Select {...props} onChange={event => onChange(event.target.value)} />;
}
