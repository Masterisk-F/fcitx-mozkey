#ifndef _WIN32
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <chrono>
#include <thread>
#include <iostream>
#endif

#include <string>
#include "testing/gunit.h"

namespace mozc {
namespace zenz_scorer {
namespace {

#pragma pack(push, 1)
struct ZenzWireRequestHeader {
  uint32_t magic;
  uint16_t version;
  uint16_t kind;
  uint32_t generation;
  uint32_t timeout_msec;
  uint32_t max_output_chars;
  uint32_t prompt_size;
};

struct ZenzWireResponseHeader {
  uint32_t magic;
  uint16_t version;
  uint16_t kind;
  uint32_t generation;
  uint32_t status;
  uint32_t latency_msec;
  uint32_t value_size;
  uint32_t debug_size;
};
#pragma pack(pop)

constexpr uint32_t kZenzWireMagic = 0x315A4E5A;  // "ZNZ1"
constexpr uint16_t kZenzWireVersion = 1;
constexpr uint16_t kZenzWireKindRequest = 1;

TEST(ScorerSignalTest, TerminateGracefully) {
#ifndef _WIN32
  // Get directory of current executable
  char exe_path[4096];
  ssize_t len = ::readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
  ASSERT_GT(len, 0);
  exe_path[len] = '\0';
  std::string dir = ".";
  std::string path(exe_path);
  size_t pos = path.find_last_of('/');
  if (pos != std::string::npos) {
    dir = path.substr(0, pos);
  }
  std::string scorer_path = dir + "/mozc_zenz_scorer";

  // Create a unique, short temp directory for HOME to avoid socket path limits (>108 chars) in Bazel sandbox
  std::string temp_home = "/tmp/zenz_home_" + std::to_string(getpid());
  ::mkdir(temp_home.c_str(), 0755);

  pid_t pid = fork();
  ASSERT_GE(pid, 0);

  if (pid == 0) {
    // Child: run mozc_zenz_scorer
    setenv("HOME", temp_home.c_str(), 1);
    
    // We pass dummy values or let it use defaults
    char* argv[] = {const_cast<char*>("mozc_zenz_scorer"), nullptr};
    ::execv(scorer_path.c_str(), argv);
    std::cerr << "execv failed: " << strerror(errno) << std::endl;
    ::_exit(127);
  }

  // Parent: wait for scorer to start up (up to 1.5 seconds)
  std::this_thread::sleep_for(std::chrono::milliseconds(1500));

  // Send SIGTERM
  int kill_ret = kill(pid, SIGTERM);
  ASSERT_EQ(kill_ret, 0);

  // Wait for child to exit (timeout after 5 seconds)
  int status = 0;
  bool exited = false;
  for (int i = 0; i < 50; ++i) {
    pid_t wait_ret = waitpid(pid, &status, WNOHANG);
    if (wait_ret == pid) {
      exited = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }

  EXPECT_TRUE(exited) << "mozc_zenz_scorer hung or did not exit within 5 seconds";

  if (exited) {
    EXPECT_TRUE(WIFEXITED(status));
    EXPECT_EQ(WEXITSTATUS(status), 0);
  } else {
    // Force kill if it hung
    kill(pid, SIGKILL);
    waitpid(pid, nullptr, 0);
  }

  // Clean up temp home
  std::string socket_path = temp_home + "/.mozc_zenz_scorer_pipe";
  ::unlink(socket_path.c_str());
  ::rmdir(temp_home.c_str());
#endif
}

TEST(ScorerSignalTest, UnixSocketLoopTest) {
#ifndef _WIN32
  char exe_path[4096];
  ssize_t len = ::readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
  ASSERT_GT(len, 0);
  exe_path[len] = '\0';
  std::string dir = ".";
  std::string path(exe_path);
  size_t pos = path.find_last_of('/');
  if (pos != std::string::npos) {
    dir = path.substr(0, pos);
  }
  std::string scorer_path = dir + "/mozc_zenz_scorer";

  std::string temp_home = "/tmp/zenz_home_loop_" + std::to_string(getpid());
  ::mkdir(temp_home.c_str(), 0755);

  pid_t pid = fork();
  ASSERT_GE(pid, 0);

  if (pid == 0) {
    setenv("HOME", temp_home.c_str(), 1);
    char* argv[] = {const_cast<char*>("mozc_zenz_scorer"), nullptr};
    ::execv(scorer_path.c_str(), argv);
    ::_exit(127);
  }

  // Parent: wait for scorer to start up
  std::this_thread::sleep_for(std::chrono::milliseconds(1500));

  // Connect to unix domain socket
  std::string socket_path = temp_home + "/.mozc_zenz_scorer_pipe";
  int sock = ::socket(AF_UNIX, SOCK_STREAM, 0);
  ASSERT_GE(sock, 0);

  struct sockaddr_un addr = {};
  addr.sun_family = AF_UNIX;
  ::strncpy(addr.sun_path, socket_path.c_str(), sizeof(addr.sun_path) - 1);

  int conn_ret = ::connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
  ASSERT_EQ(conn_ret, 0) << "Failed to connect to UNIX domain socket";

  // Send bad request header (wrong magic)
  ZenzWireRequestHeader req = {};
  req.magic = 0xDEADBEEF; // Bad magic
  req.version = kZenzWireVersion;
  req.kind = kZenzWireKindRequest;
  req.prompt_size = 10;

  ssize_t written = ::write(sock, &req, sizeof(req));
  ASSERT_EQ(written, sizeof(req));

  // Read response
  ZenzWireResponseHeader res = {};
  ssize_t read_bytes = ::read(sock, &res, sizeof(res));
  ASSERT_EQ(read_bytes, sizeof(res));

  EXPECT_NE(res.status, 0);
  EXPECT_GT(res.debug_size, 0);

  char debug_buf[256] = {};
  if (res.debug_size > 0 && res.debug_size < sizeof(debug_buf)) {
    ::read(sock, debug_buf, res.debug_size);
    EXPECT_STREQ(debug_buf, "bad_request_header");
  }

  ::close(sock);

  // Send SIGTERM and wait
  kill(pid, SIGTERM);
  int status = 0;
  waitpid(pid, &status, 0);

  ::unlink(socket_path.c_str());
  ::rmdir(temp_home.c_str());
#endif
}

}  // namespace
}  // namespace zenz_scorer
}  // namespace mozc
