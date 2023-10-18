set_property(DIRECTORY . APPEND PROPERTY COMPILE_DEFINITIONS ${DEFINES})

# see https://cmake.org/Wiki/CMake_RPATH_handling#Always_full_RPATH
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(LIB ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR})
list(FIND CMAKE_PLATFORM_IMPLICIT_LINK_DIRECTORIES ${LIB} isSystemDir)
if("${isSystemDir}" STREQUAL "-1")
  set(CMAKE_INSTALL_RPATH ${LIB})
endif()

include(FindPackageHandleStandardArgs)

find_library(HTTP_PARSER_LIB NAMES http_parser)
if(NOT HTTP_PARSER_LIB)
  message(FATAL_ERROR "http-parser not found")
endif()
find_path(HTTP_PARSER_INCLUDE http_parser.h PATH_SUFFIXES include)
find_package_handle_standard_args(http-parser
  DEFAULT_MSG HTTP_PARSER_LIB HTTP_PARSER_INCLUDE
)

set(TARGETS client server)
if(HAVE_NETMAP_H)
  set(TARGETS ${TARGETS} client-warp server-warp)
endif()

if(NOT WITH_MINICRYPTO)
  set(CRYPTOLIBS picotls-openssl ${OPENSSL_LIBRARIES})
else()
  set(CRYPTOLIBS picotls-minicrypto)
endif()

foreach(TARGET ${TARGETS})
  if(${TARGET} MATCHES ".*-warp")
    string(REGEX REPLACE "-warp$" "" SOURCE ${TARGET})
    add_executable(${TARGET} ${SOURCE}.c)
    target_link_libraries(${TARGET} PRIVATE
      lib${PROJECT_NAME}-warp
      ${HTTP_PARSER_LIB}
      picohttp-core
      ${CRYPTOLIBS}
    )
  else()
    add_executable(${TARGET} ${TARGET}.c)
    target_link_libraries(${TARGET} PRIVATE
      lib${PROJECT_NAME}
      ${HTTP_PARSER_LIB}
      picohttp-core
      ${CRYPTOLIBS}
    )
    if("${CMAKE_C_COMPILER_ID}" STREQUAL "Clang" AND
       CMAKE_C_COMPILER_VERSION VERSION_GREATER 9)
      target_compile_options(${TARGET} PRIVATE -Wno-poison-system-directories)
    endif()
  endif()

  target_include_directories(${TARGET}
    SYSTEM PRIVATE
      ${HTTP_PARSER_INCLUDE}
      $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/lib/deps/picoquic>
  )

  if(DSYMUTIL)
    add_custom_command(TARGET ${TARGET} POST_BUILD
      COMMAND ${DSYMUTIL} ARGS $<TARGET_FILE:${TARGET}>
    )
  endif()

  install(TARGETS ${TARGET} DESTINATION bin)
endforeach()

add_custom_target(${PROJECT_NAME} DEPENDS client server)


