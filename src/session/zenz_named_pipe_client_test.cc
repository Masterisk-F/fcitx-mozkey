#include "session/zenz_named_pipe_client.h"

#ifndef _WIN32
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#endif

#include <string>
#include <thread>
#include <fstream>

#include "testing/gunit.h"

namespace mozc {
namespace session {

bool LaunchZenzScorerIfNeeded();

namespace {

TEST(ZenzNamedPipeClientTest, LinuxFallback) {
#ifndef _WIN32
  // Create a temporary directory to act as HOME
  char temp_dir[] = "/tmp/zenz_test_XXXXXX";
  EXPECT_TRUE(mkdtemp(temp_dir) != nullptr);

  setenv("HOME", temp_dir, 1);

  std::string socket_path = std::string(temp_dir) + "/.mozc_zenz_scorer_pipe";

  // Create a dummy Unix domain socket
  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  EXPECT_GE(fd, 0);

  struct sockaddr_un addr;
  memset(&addr, 0, sizeof(addr));
  addr.sun_family = AF_UNIX;
  strncpy(addr.sun_path, socket_path.c_str(), sizeof(addr.sun_path) - 1);

  EXPECT_EQ(bind(fd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)), 0);
  EXPECT_EQ(listen(fd, 1), 0);

  std::thread server_thread([fd]() {
    int client_fd = accept(fd, nullptr, nullptr);
    if (client_fd >= 0) {
      close(client_fd);
    }
  });

  ZenzNamedPipeClient client;
  ZenzLiveRequest request;
  // Windows-style named pipe path
  request.pipe_name = "\\\\.\\pipe\\mozc_zenz_scorer";
  request.timeout_msec = 100;

  // The client should fallback to ~/.mozc_zenz_scorer_pipe in Linux
  ZenzLiveResponse response = client.Convert(request);

  server_thread.join();

  // Since our dummy socket closes immediately, the client will fail at write or read,
  // but crucially it should NOT fail with "pipe_open_failed" or "invalid_pipe_name".
  EXPECT_NE(response.debug, "pipe_open_failed");
  EXPECT_NE(response.debug, "invalid_pipe_name");

  close(fd);
  unlink(socket_path.c_str());
  rmdir(temp_dir);
#endif
}

TEST(ZenzNamedPipeClientTest, LaunchScorerViaPosixSpawn) {
#ifndef _WIN32
  // Sleep to clear the 2-second launch throttle from any previous tests
  std::this_thread::sleep_for(std::chrono::milliseconds(2100));

  const char* test_tmpdir = getenv("TEST_TMPDIR");
  std::string dir = test_tmpdir ? test_tmpdir : "/tmp";
  std::string dummy_path = dir + "/mozc_zenz_scorer";
  {
    std::ofstream os(dummy_path);
    os << "#!/bin/sh\nexit 0\n";
  }
  chmod(dummy_path.c_str(), 0755);

  // Set override environment variable for the test
  setenv("MOZC_TEST_SCORER_PATH", dummy_path.c_str(), 1);

  bool result = LaunchZenzScorerIfNeeded();
  EXPECT_TRUE(result);

  unsetenv("MOZC_TEST_SCORER_PATH");
  unlink(dummy_path.c_str());
#endif
}

}  // namespace
}  // namespace session
}  // namespace mozc
