#ifndef MOZC_ZENZ_SCORER_CONSTANTS_H_
#define MOZC_ZENZ_SCORER_CONSTANTS_H_

namespace mozc {
namespace zenz_scorer {

constexpr wchar_t kDefaultPipeName[] = L"\\\\.\\pipe\\mozc_zenz_scorer";
constexpr wchar_t kSingleInstanceMutexName[] = L"Local\\MozcZenzScorerSingleInstance";

}  // namespace zenz_scorer
}  // namespace mozc

#endif  // MOZC_ZENZ_SCORER_CONSTANTS_H_
