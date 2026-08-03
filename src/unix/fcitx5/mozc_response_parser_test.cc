#include "unix/fcitx5/mozc_response_parser.h"

#include <string>
#include <vector>

#include "protocol/commands.pb.h"
#include "unix/fcitx5/mozc_engine.h"
#include "unix/fcitx5/mozc_state.h"
#include "unix/fcitx5/fcitx_key_event_handler.h"
#include "unix/fcitx5/surrounding_text_util.h"
#include "unix/fcitx5/mozc_client_interface.h"
#include "testing/gunit.h"

//
// Stub implementations for MozcEngine and MozcState used by MozcResponseParser
//

namespace {
mozc::commands::SessionCommand g_last_scheduled_command;
uint32_t g_last_scheduled_delay = 0;
bool g_schedule_live_conversion_called = false;
}

namespace fcitx {

// Stub MozcEngine methods
MozcEngine::MozcEngine(Instance* instance) : instance_(instance), factory_([](InputContext&) { return nullptr; }) {}
MozcEngine::~MozcEngine() = default;

AddonInstance* MozcEngine::clipboardAddon() { return nullptr; }

MozcState* MozcEngine::mozcState(InputContext* ic) {
  // We use the InputContext pointer as a MozcState pointer in tests.
  return reinterpret_cast<MozcState*>(ic);
}

void MozcEngine::reloadConfig() {}
void MozcEngine::save() {}
void MozcEngine::setConfig(const fcitx::RawConfig& config) {}
void MozcEngine::keyEvent(const fcitx::InputMethodEntry& entry, fcitx::KeyEvent& keyEvent) {}
void MozcEngine::activate(const fcitx::InputMethodEntry& entry, fcitx::InputContextEvent& event) {}
void MozcEngine::deactivate(const fcitx::InputMethodEntry& entry, fcitx::InputContextEvent& event) {}
void MozcEngine::reset(const fcitx::InputMethodEntry& entry, fcitx::InputContextEvent& event) {}
std::string MozcEngine::subMode(const fcitx::InputMethodEntry& entry, fcitx::InputContext& ic) { return ""; }
std::string MozcEngine::subModeIconImpl(const fcitx::InputMethodEntry& entry, fcitx::InputContext& ic) { return ""; }

// Stub MozcState methods
MozcState::MozcState(InputContext* ic, MozcEngine* engine) {}
MozcState::~MozcState() {}

MozcClientInterface* MozcState::GetClient() const { return nullptr; }

bool MozcState::Paging(bool prev) { return false; }

void MozcState::SelectCandidate(int idx) {}

bool MozcState::SendCommand(const mozc::commands::SessionCommand& session_command,
                            mozc::commands::Output* new_output) {
  return true;
}

void MozcState::SetAuxString(const std::string& str) {}

void MozcState::SetCompositionMode(mozc::commands::CompositionMode mode, bool updateUI) {}

void MozcState::SetPreeditInfo(Text preedit_info) {}

void MozcState::SetResultString(const std::string& result_string) {}

void MozcState::SetUrl(const std::string& url) {}

void MozcState::SetUsage(const std::string& title, const std::string& description) {}

void MozcState::ScheduleLiveConversion(const mozc::commands::SessionCommand& command,
                                       uint32_t delay_millisec) {
  g_schedule_live_conversion_called = true;
  g_last_scheduled_command = command;
  g_last_scheduled_delay = delay_millisec;
}

// Stub createClient
std::unique_ptr<MozcClientInterface> createClient() {
  return nullptr;
}

// Stub GetSurroundingText is NOT needed because we linked :surrounding_text_util
}  // namespace fcitx

namespace mozc {
namespace fcitx_test {
namespace {

class MozcResponseParserTest : public testing::Test {
 protected:
  void SetUp() override {
    g_schedule_live_conversion_called = false;
    g_last_scheduled_command.Clear();
    g_last_scheduled_delay = 0;
  }
};

TEST_F(MozcResponseParserTest, ApplyZenzLiveCorrectionTest) {
  // Setup dummy objects
  fcitx::MozcEngine engine(nullptr);
  fcitx::MozcResponseParser parser(&engine);

  // We don't actually need a real InputContext, we just need a non-null pointer
  // that engine.mozcState() can cast to a MozcState*.
  // Let's create a dummy MozcState object to act as the returned pointer.
  fcitx::MozcState dummy_state(nullptr, nullptr);
  fcitx::InputContext* dummy_ic = reinterpret_cast<fcitx::InputContext*>(&dummy_state);

  commands::Output output;
  output.set_consumed(true);

  auto* callback = output.mutable_callback();
  callback->set_delay_millisec(1234);

  auto* session_command = callback->mutable_session_command();
  session_command->set_type(commands::SessionCommand::APPLY_ZENZ_LIVE_CORRECTION);
  session_command->set_live_conversion_generation(42);
  session_command->set_live_conversion_key("zenz");

  EXPECT_TRUE(parser.ParseResponse(output, dummy_ic));

  EXPECT_TRUE(g_schedule_live_conversion_called);
  EXPECT_EQ(g_last_scheduled_command.type(), commands::SessionCommand::APPLY_ZENZ_LIVE_CORRECTION);
  EXPECT_EQ(g_last_scheduled_command.live_conversion_generation(), 42);
  EXPECT_EQ(g_last_scheduled_command.live_conversion_key(), "zenz");
  EXPECT_EQ(g_last_scheduled_delay, 1234);
}

}  // namespace
}  // namespace fcitx_test
}  // namespace mozc
