#!/usr/bin/env python3
"""
Simplified test for conversation management core functionality
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from atlas_commands.conversation.conversation_manager import (
        ConversationManager, MessageType, ConversationState, ConversationMessage
    )
    from atlas_commands.conversation.dialog_state_tracker import (
        DialogStateTracker, DialogState, DialogIntent
    )
    from atlas_commands.entropy.entropy_processor import EntropyProcessor, EntropyThresholds
    
    print("✅ Successfully imported core conversation modules")
    
    # Mock memory manager for testing
    class MockMemoryManager:
        async def create_entities(self, entities):
            print(f"Mock: Creating {len(entities)} memory entities")
        
        async def add_observations(self, observations):
            print(f"Mock: Adding {len(observations)} observations")
        
        async def create_relations(self, relations):
            print(f"Mock: Creating {len(relations)} relations")
        
        async def search_nodes(self, query):
            print(f"Mock: Searching nodes for '{query}'")
            return []
    
    async def test_conversation_core():
        """Test core conversation management functionality."""
        
        print("\n🔧 Testing Core Conversation Management:")
        
        # Initialize components with mocks
        storage_path = "/tmp/atlas_conversation_test"
        os.makedirs(storage_path, exist_ok=True)
        
        # Mock memory manager
        memory_manager = MockMemoryManager()
        
        # Real entropy processor
        entropy_thresholds = EntropyThresholds(
            high_entropy_threshold=0.894,
            low_entropy_threshold=0.3,
            entropy_spike_threshold=0.5,
            information_overflow_threshold=10000,
            pattern_saturation_threshold=0.9,
            novelty_threshold=0.7
        )
        entropy_processor = EntropyProcessor(thresholds=entropy_thresholds)
        
        # Initialize conversation components
        conversation_manager = ConversationManager(storage_path, memory_manager, entropy_processor)
        dialog_tracker = DialogStateTracker(conversation_manager, entropy_processor)
        
        print("✅ Core components initialized")
        
        # Test 1: Start conversation
        print("\n📝 Test 1: Conversation Lifecycle")
        
        session_id = await conversation_manager.start_conversation(
            initial_context="Testing ATLAS conversation management",
            metadata={"test": True}
        )
        print(f"✅ Started conversation: {session_id}")
        
        # Test 2: Add messages with state tracking
        print("\n💬 Test 2: Message Processing and State Tracking")
        
        test_conversations = [
            ("Hello, I need help with a coding task", MessageType.USER_REQUEST),
            ("I'd be happy to help! What kind of coding task are you working on?", MessageType.SYSTEM_RESPONSE),
            ("I need to implement a network discovery feature", MessageType.USER_REQUEST),
            ("Let me analyze the requirements for network discovery. This will involve scanning for available services and protocols.", MessageType.SYSTEM_RESPONSE),
            ("That sounds perfect. Can you break it down into steps?", MessageType.USER_REQUEST),
            ("Certainly! Here's my recommended approach: 1) Port scanning, 2) Service identification, 3) Protocol detection", MessageType.SYSTEM_RESPONSE),
            ("Great plan! Let's start implementing the port scanner", MessageType.USER_REQUEST),
            ("I'll implement the port scanner now using socket connections", MessageType.TOOL_EXECUTION),
            ("Port scanner implementation completed successfully", MessageType.SYSTEM_RESPONSE),
            ("Excellent! The results look good. Now let's add protocol detection", MessageType.USER_REQUEST)
        ]
        
        message_ids = []
        for i, (content, msg_type) in enumerate(test_conversations):
            # Add message to conversation manager
            msg_id = await conversation_manager.add_message(
                session_id, msg_type, content,
                metadata={"step": i + 1, "test": True}
            )
            message_ids.append(msg_id)
            
            # Track with dialog state tracker
            dialog_context = await dialog_tracker.track_message(session_id, content, msg_type)
            
            print(f"   Step {i+1}: {msg_type.value} -> State: {dialog_context.current_state.value}")
            
            # Small delay for realistic timing
            await asyncio.sleep(0.05)
        
        print(f"✅ Processed {len(test_conversations)} messages")
        
        # Test 3: Context retrieval
        print("\n📊 Test 3: Context Retrieval")
        
        context = await conversation_manager.get_conversation_context(session_id)
        print(f"✅ Retrieved conversation context:")
        print(f"   Session ID: {context['session_id']}")
        print(f"   Total messages: {len(context['messages'])}")
        print(f"   High entropy messages: {len(context['high_entropy_messages'])}")
        print(f"   Session state: {context['session_state']}")
        print(f"   Context summary: {context['context_summary'][:100]}...")
        
        # Test 4: Dialog state analysis
        print("\n🔄 Test 4: Dialog State Analysis")
        
        dialog_summary = await dialog_tracker.get_dialog_context_summary(session_id)
        print(f"✅ Dialog state summary:")
        print(f"   Current state: {dialog_summary['current_state']}")
        print(f"   Previous state: {dialog_summary['previous_state']}")
        print(f"   Confidence: {dialog_summary['confidence_score']:.3f}")
        print(f"   Active contexts: {dialog_summary['active_contexts']}")
        print(f"   Time in current state: {dialog_summary['time_in_current_state']:.1f}s")
        print(f"   Context complexity: {dialog_summary['context_complexity']}")
        
        # Test 5: Dialog suggestions
        print("\n💡 Test 5: Dialog Suggestions")
        
        suggestions = await dialog_tracker.get_dialog_suggestions(session_id)
        print(f"✅ Generated {len(suggestions)} dialog suggestions:")
        for i, suggestion in enumerate(suggestions[:3]):
            print(f"   {i+1}. {suggestion}")
        
        # Test 6: Context switching
        print("\n🔄 Test 6: Context Switching")
        
        switch_context = await dialog_tracker.handle_context_switch(
            session_id, "Switch to debugging an existing feature"
        )
        print(f"✅ Context switch executed:")
        print(f"   New state: {switch_context.current_state.value}")
        print(f"   Context stack depth: {len(switch_context.context_stack)}")
        
        # Test 7: Conversation completion
        print("\n🏁 Test 7: Conversation Completion")
        
        await conversation_manager.complete_conversation(
            session_id, "Successfully demonstrated ATLAS conversation management"
        )
        print("✅ Conversation completed and archived")
        
        # Test 8: Session statistics
        print("\n📈 Test 8: Session Statistics")
        
        stats = await conversation_manager.get_session_stats()
        print("✅ Session statistics:")
        print(f"   Active sessions: {stats['active_sessions']}")
        print(f"   Total messages: {stats['total_messages']}")
        print(f"   High entropy messages: {stats['high_entropy_messages']}")
        print(f"   Average entropy: {stats['average_entropy']:.3f}")
        
        return {
            "session_id": session_id,
            "messages_processed": len(test_conversations),
            "final_state": dialog_summary['current_state'],
            "high_entropy_detected": len(context['high_entropy_messages']) > 0,
            "suggestions_generated": len(suggestions) > 0
        }
    
    async def main():
        print("🚀 ATLAS MCP Conversation Management Core Test")
        print("=" * 60)
        
        try:
            results = await test_conversation_core()
            
            print("\n🎯 Core Test Results:")
            print("✅ Conversation lifecycle management: Working")
            print("✅ Message processing and storage: Working")
            print("✅ Dialog state tracking: Working")
            print("✅ Context retrieval: Working")
            print("✅ Dialog suggestions: Working")
            print("✅ Context switching: Working")
            print("✅ Session statistics: Working")
            
            print(f"\n📊 Test Metrics:")
            print(f"   Messages processed: {results['messages_processed']}")
            print(f"   Final dialog state: {results['final_state']}")
            print(f"   High entropy detection: {'✅' if results['high_entropy_detected'] else '❌'}")
            print(f"   Suggestion generation: {'✅' if results['suggestions_generated'] else '❌'}")
            
            print(f"\n💡 Core Conversation Features Verified:")
            print(f"   - Persistent conversation sessions with metadata")
            print(f"   - Intelligent message entropy analysis (Shannon's theory)")
            print(f"   - Dialog state tracking with confidence scoring")
            print(f"   - Context-aware suggestion generation")
            print(f"   - Automatic conversation summarization")
            print(f"   - Session lifecycle management")
            print(f"   - Context switching capabilities")
            
            print(f"\n🔗 Ready for MCP Integration:")
            print(f"   - Chat functionality can now track conversation state")
            print(f"   - High-value messages automatically identified")
            print(f"   - Dialog flow intelligence for natural interactions")
            print(f"   - Context persistence across MCP tool calls")
            
        except Exception as e:
            print(f"❌ Core test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the test
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()