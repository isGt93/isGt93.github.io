import type { NavBarConfig } from "../types/config";
import { LinkPreset } from "../types/config";

export const navBarConfig: NavBarConfig = {
  links: [LinkPreset.Home, LinkPreset.Archive, LinkPreset.About,
    { name: "GitHub", url: "https://github.com/isGt93/isGt93.github.io", icon: "fa7-brands:github", external: true }],
};
