import { parseSseBlock } from "./useRunStream";

test("parses a live event and ignores control frames", () => {
  expect(
    parseSseBlock(
      'id: event-1\nevent: run.status\ndata: {"event_id":"event-1","event_type":"run.status"}',
    ),
  ).toEqual({ event_id: "event-1", event_type: "run.status" });
  expect(parseSseBlock("retry: 2000")).toBeNull();
});
