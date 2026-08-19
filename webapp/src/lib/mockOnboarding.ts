/**
 * Declared MOCK-until-onboarded sample content.
 *
 * Per ONBOARDING_STANDARD.md: while the robot bridge is not configured the dashboard
 * may show clearly-badged sample data so the UI is not a blank desert. Every mock
 * surface carries a MOCK badge; content clears once health reports configured=true.
 * Sample actors are obviously fake names (Joe Mocky, Sandra Mockinger).
 */
export interface MockRobotSample {
  robot_id: string;
  display_name: string;
  platform: string;
  status: string;
}

export const MOCK_ROBOTS: MockRobotSample[] = [
  {
    robot_id: "boomy",
    display_name: "Boomy (Yahboom)",
    platform: "ROSMASTER X3",
    status: "available",
  },
  { robot_id: "bumi", display_name: "Bumi (biped)", platform: "bumi-mcp", status: "available" },
  {
    robot_id: "vboomy",
    display_name: "vBoomy (virtual)",
    platform: "Resonite OSC",
    status: "available",
  },
];

export const MOCK_SESSION = {
  frames_in: 1284,
  active: true,
  robot: "boomy",
  note: "Sample session while onboarding is pending - real robot not connected.",
};

export const MOCK_LIVEKIT = {
  running: false,
  room: "teleop-boomy",
  note: "Sample LiveKit status - no SFU connected yet.",
};
