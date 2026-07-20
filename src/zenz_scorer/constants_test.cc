#include "zenz_scorer/constants.h"
#include <string>
#include "testing/gunit.h"

namespace mozc {
namespace zenz_scorer {
namespace {

TEST(ConstantsTest, VerifyWindowsConstants) {
  EXPECT_EQ(std::wstring(kDefaultPipeName), L"\\\\.\\pipe\\mozc_zenz_scorer");
  EXPECT_EQ(std::wstring(kSingleInstanceMutexName), L"Local\\MozcZenzScorerSingleInstance");
}

}  // namespace
}  // namespace zenz_scorer
}  // namespace mozc
