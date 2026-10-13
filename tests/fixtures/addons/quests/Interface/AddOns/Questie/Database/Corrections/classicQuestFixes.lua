function QuestieQuestFixes:Load()
    local questKeys = QuestieDB.questKeys

    return {
        [7] = { -- Kobold Camp Cleanup
            [questKeys.nextQuestInChain] = 15,
        },
    }
end
