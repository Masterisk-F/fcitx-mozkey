#ifndef _WIN32
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
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

}  // namespace
}  // namespace zenz_scorer
}  // namespace mozc
