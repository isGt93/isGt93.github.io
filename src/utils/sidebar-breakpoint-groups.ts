import { isDeepStrictEqual } from "node:util";

export type SidebarBreakpoint = "mobile" | "tablet" | "desktop";

export interface SidebarBreakpointGroup<T> {
	breakpoints: SidebarBreakpoint[];
	components: T[];
}

/** Merge complete ordered configurations, never individual overlapping widgets. */
export function groupSidebarBreakpoints<T>(
	entries: { breakpoint: SidebarBreakpoint; components: T[] }[],
): SidebarBreakpointGroup<T>[] {
	const groups: SidebarBreakpointGroup<T>[] = [];
	for (const { breakpoint, components } of entries) {
		if (components.length === 0) continue;
		const existing = groups.find((group) =>
			isDeepStrictEqual(group.components, components),
		);
		if (existing) existing.breakpoints.push(breakpoint);
		else groups.push({ breakpoints: [breakpoint], components });
	}
	return groups;
}

// Keep complete class literals so Tailwind includes every visibility rule.
const visibility: Record<string, string> = {
	mobile: "flex md:hidden",
	tablet: "hidden md:flex lg:hidden",
	desktop: "hidden lg:flex",
	"mobile,tablet": "flex lg:hidden",
	"mobile,desktop": "flex md:hidden lg:flex",
	"tablet,desktop": "hidden md:flex",
	"mobile,tablet,desktop": "flex",
};

export function sidebarBreakpointVisibility(
	breakpoints: SidebarBreakpoint[],
): string {
	return visibility[breakpoints.join(",")] ?? "hidden";
}
