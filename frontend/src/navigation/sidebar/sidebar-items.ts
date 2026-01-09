import {
  ChartBar,
  ClipboardList,
  GraduationCap,
  LayoutDashboard,
  type LucideIcon,
  Radio,
  Settings,
  Settings2,
  Target,
} from "lucide-react";

export interface NavSubItem {
  title: string;
  url: string;
  icon?: LucideIcon;
  comingSoon?: boolean;
  newTab?: boolean;
  isNew?: boolean;
}

export interface NavMainItem {
  title: string;
  url: string;
  icon?: LucideIcon;
  subItems?: NavSubItem[];
  comingSoon?: boolean;
  newTab?: boolean;
  isNew?: boolean;
}

export interface NavGroup {
  id: number;
  label?: string;
  items: NavMainItem[];
}

export const sidebarItems: NavGroup[] = [
  {
    id: 1,
    label: "Jira Feedback",
    items: [
      {
        title: "Overview",
        url: "/dashboard/overview",
        icon: LayoutDashboard,
      },
      {
        title: "Issues",
        url: "/dashboard/issues",
        icon: ClipboardList,
      },
      {
        title: "Rubric Config",
        url: "/dashboard/rubric",
        icon: Settings2,
      },
      {
        title: "Students",
        url: "/dashboard/students",
        icon: GraduationCap,
      },
      {
        title: "Skill Analysis",
        url: "/dashboard/skills",
        icon: Target,
      },
      {
        title: "Analytics",
        url: "/dashboard/analytics",
        icon: ChartBar,
      },
      {
        title: "Live Monitor",
        url: "/dashboard/monitor",
        icon: Radio,
      },
    ],
  },
  {
    id: 2,
    label: "Settings",
    items: [
      {
        title: "Settings",
        url: "/dashboard/settings",
        icon: Settings,
      },
    ],
  },
];
