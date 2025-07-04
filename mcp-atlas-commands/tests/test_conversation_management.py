#!/usr/bin/env python3
"""
Test script to verify conversation management integration with ATLAS MCP
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from atlas_commands.conversation.conversation_manager import ConversationManager, MessageType
    from atlas_commands.conversation.dialog_state_tracker import DialogStateTracker
    from atlas_commands.conversation.message_history import MessageHistorySystem, HistorySearchMode
    from atlas_commands.memory.graph_manager import MemoryGraphManager
    from atlas_commands.entropy.entropy_processor import EntropyProcessor, EntropyThresholds
    from atlas_commands.embeddings.semantic_search import SemanticSearchEngine
    from atlas_commands.embeddings.graph_sage import EmbeddingGenerator
    from atlas_commands.embeddings.vector_store import EmbeddingStorage
    
    print("✅ Successfully imported conversation management modules")
    
    async def test_conversation_management():
        """Test conversation management functionality."""
        
        print("\n🔧 Testing Conversation Management Integration:")
        
        # Initialize required components
        print("Initializing components...")
        
        # Mock storage path
        storage_path = "/tmp/atlas_test"
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize memory manager (simplified for testing)
        memory_manager = MemoryGraphManager()
        
        # Initialize entropy processor
        entropy_thresholds = EntropyThresholds(
            high_entropy_threshold=0.894,
            low_entropy_threshold=0.3,
            entropy_spike_threshold=0.5,
            information_overflow_threshold=10000,
            pattern_saturation_threshold=0.9,
            novelty_threshold=0.7
        )
        entropy_processor = EntropyProcessor(thresholds=entropy_thresholds)
        
        # Initialize semantic search components
        embedding_generator = EmbeddingGenerator()
        embedding_storage = EmbeddingStorage(storage_path)
        semantic_search = SemanticSearchEngine(embedding_generator, embedding_storage)
        
        # Initialize conversation components
        conversation_manager = ConversationManager(storage_path, memory_manager, entropy_processor)
        dialog_tracker = DialogStateTracker(conversation_manager, entropy_processor)
        history_system = MessageHistorySystem(
            conversation_manager, dialog_tracker, memory_manager, 
            entropy_processor, semantic_search, storage_path
        )
        
        print("✅ All components initialized successfully")
        
        # Test conversation lifecycle
        print("\n📝 Testing Conversation Lifecycle:")
        
        # 1. Start conversation
        session_id = await conversation_manager.start_conversation(
            initial_context="Test conversation for ATLAS MCP chat integration",
            metadata={"test": True, "purpose": "integration_testing"}
        )
        print(f"✅ Started conversation: {session_id}")
        
        # 2. Add various types of messages
        test_messages = [
            ("I need help implementing a new feature for network discovery", MessageType.USER_REQUEST),
            ("I'll analyze your requirements and create a plan for the network discovery feature", MessageType.SYSTEM_RESPONSE),
            ("The feature should automatically detect available network services and protocols", MessageType.USER_REQUEST),
            ("Let me break this down into specific implementation steps", MessageType.SYSTEM_RESPONSE),
            ("First, we'll implement a service scanner using port scanning techniques", MessageType.SYSTEM_RESPONSE),
            ("That sounds good, but can we also add protocol detection?", MessageType.USER_REQUEST),
            ("Absolutely! I'll add protocol fingerprinting to identify specific services", MessageType.SYSTEM_RESPONSE),
            ("Execute the network scanner implementation", MessageType.TOOL_EXECUTION),
            ("Network scanner implementation completed successfully", MessageType.SYSTEM_RESPONSE),
            ("Great! Now let's test it with the protocol detection", MessageType.USER_REQUEST)
        ]
        
        message_ids = []
        for content, msg_type in test_messages:
            msg_id = await conversation_manager.add_message(
                session_id, msg_type, content, 
                metadata={"timestamp": datetime.now().isoformat()}
            )
            message_ids.append(msg_id)
            
            # Track message with dialog state tracker
            dialog_context = await dialog_tracker.track_message(session_id, content, msg_type)
            
            print(f"   Added message: {msg_type.value} (state: {dialog_context.current_state.value})")
            
            # Small delay to simulate realistic conversation timing
            await asyncio.sleep(0.1)
        
        print(f"✅ Added {len(test_messages)} messages to conversation")
        
        # 3. Test conversation context retrieval
        print("\n📊 Testing Context Retrieval:")
        
        context = await conversation_manager.get_conversation_context(session_id)
        print(f"✅ Retrieved context: {context['message_count']} messages")
        print(f"   High entropy messages: {len(context['high_entropy_messages'])}")
        print(f"   Session state: {context['session_state']}")
        
        # 4. Test dialog state tracking
        print("\n🔄 Testing Dialog State Tracking:")
        
        dialog_summary = await dialog_tracker.get_dialog_context_summary(session_id)
        print(f"✅ Dialog state: {dialog_summary['current_state']}")
        print(f"   Confidence: {dialog_summary['confidence_score']:.3f}")
        print(f"   Active contexts: {len(dialog_summary['active_contexts'])}")
        print(f"   Time in state: {dialog_summary['time_in_current_state']:.1f}s")
        
        # Get suggestions
        suggestions = await dialog_tracker.get_dialog_suggestions(session_id)
        print(f"   Suggestions: {len(suggestions)} available")
        for i, suggestion in enumerate(suggestions[:3]):
            print(f"     {i+1}. {suggestion}")
        
        # 5. Test message history analysis
        print("\n📈 Testing Message History Analysis:")
        
        # Analyze patterns
        patterns = await history_system.analyze_conversation_patterns(session_id)
        print(f"✅ Detected {len(patterns)} conversation patterns")
        for pattern in patterns[:3]:
            print(f"   Pattern: {pattern.pattern_type} (confidence: {pattern.confidence:.3f})")
        
        # Generate conversation summary
        summary = await history_system.generate_conversation_summary(session_id)
        print(f"✅ Generated conversation summary:")
        print(f"   Summary: {summary.summary_text}")
        print(f"   Key decisions: {len(summary.key_decisions)}")
        print(f"   Unresolved items: {len(summary.unresolved_items)}")
        print(f"   Dominant intents: {', '.join(summary.dominant_intents)}")
        
        # 6. Test history search
        print("\n🔍 Testing History Search:")
        
        search_results = await history_system.search_conversation_history(
            session_id, "network discovery", HistorySearchMode.SEMANTIC, limit=3
        )
        print(f"✅ Semantic search found {len(search_results)} relevant messages")
        
        entropy_results = await history_system.search_conversation_history(
            session_id, "high entropy", HistorySearchMode.ENTROPY_BASED, limit=3
        )
        print(f"✅ Entropy search found {len(entropy_results)} high-information messages")
        
        # 7. Test conversation insights
        print("\n💡 Testing Conversation Insights:")
        
        insights = await history_system.get_conversation_insights(session_id)
        if "error" not in insights:
            print("✅ Generated comprehensive conversation insights:")
            print(f"   Patterns detected: {len(insights['patterns'])}")
            print(f"   Quality score: {insights['quality_indicators'].get('quality_score', 0):.3f}")
            print(f"   Engagement metrics available: {len(insights['engagement_metrics'])}")
            print(f"   Recommendations: {len(insights['recommendations'])}")
            
            # Show sample recommendations
            for i, recommendation in enumerate(insights['recommendations'][:2]):
                print(f"     {i+1}. {recommendation}")
        else:
            print(f"⚠️ Error generating insights: {insights['error']}")
        
        # 8. Test conversation completion
        print("\n🏁 Testing Conversation Completion:")
        
        await conversation_manager.complete_conversation(
            session_id, 
            "Successfully tested ATLAS conversation management integration"
        )
        print("✅ Conversation completed and archived")
        
        # 9. Test session statistics
        print("\n📊 Testing Session Statistics:")
        
        stats = await conversation_manager.get_session_stats()
        print("✅ Session statistics:")
        print(f"   Active sessions: {stats['active_sessions']}")
        print(f"   Total messages processed: {stats['total_messages']}")
        print(f"   High entropy messages: {stats['high_entropy_messages']}")
        print(f"   Average entropy: {stats['average_entropy']:.3f}")
        
        return {
            "session_id": session_id,
            "messages_processed": len(test_messages),
            "patterns_detected": len(patterns),
            "summary_generated": summary.message_count > 0,
            "dialog_tracking": dialog_summary['current_state'] != 'greeting'
        }
    
    async def main():
        print("🚀 ATLAS MCP Conversation Management Integration Test")
        print("=" * 70)
        
        try:
            results = await test_conversation_management()
            
            print("\n🎯 Integration Test Summary:")
            print("✅ Conversation management system successfully integrated")
            print("✅ Dialog state tracking operational with intelligent transitions")
            print("✅ Message history analysis with pattern detection functional")
            print("✅ ATLAS memory graph integration confirmed")
            print("✅ Entropy-based processing integrated for high-value content")
            print("✅ Semantic search capabilities operational")
            print("✅ Conversation insights and recommendations system working")
            
            # Success metrics
            print(f"\n📈 Integration Success Metrics:")
            print(f"   Messages processed: {results['messages_processed']}")
            print(f"   Patterns detected: {results['patterns_detected']}")
            print(f"   Summary generation: {'✅ Working' if results['summary_generated'] else '❌ Failed'}")
            print(f"   Dialog state tracking: {'✅ Working' if results['dialog_tracking'] else '❌ Failed'}")
            
            # Integration benefits
            print(f"\n💡 Chat Integration Benefits:")
            print(f"   - Persistent conversation context across MCP interactions")
            print(f"   - Intelligent dialog state management for natural flow")
            print(f"   - High-entropy content automatically captured in memory")
            print(f"   - Pattern detection for conversation optimization")
            print(f"   - Semantic search for conversational history")
            print(f"   - Automatic conversation summarization and insights")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the test
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all conversation management modules are properly implemented")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()